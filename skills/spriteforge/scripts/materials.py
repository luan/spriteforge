"""Blender materials that retain UV paint under discrete RPG palette lighting."""
from pathlib import Path
import bpy
from mathutils import Vector
from style import SHADE_STOPS


def linear_color(color: str) -> tuple[float, float, float, float]:
    channels = [v / 255 for v in bytes.fromhex(color)]
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in channels) + (1,)


def pixel_material(name: str, shades: list[str], texture: Path | None = None) -> bpy.types.Material:
    """Use seven shades; optional UV paint preserves authored surface detail."""
    if len(shades) != 7:
        raise ValueError("pixel materials require seven palette shades")
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    geometry = nodes.new("ShaderNodeNewGeometry")
    dot = nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = Vector((-.5, -.65, 1)).normalized()
    links.new(geometry.outputs["Normal"], dot.inputs[0])
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
    for index, (position, color) in enumerate(zip(SHADE_STOPS, shades)):
        stop = ramp.color_ramp.elements[0] if index == 0 else ramp.color_ramp.elements.new(position)
        stop.position, stop.color = position, linear_color(color)
    links.new(dot.outputs["Value"], ramp.inputs[0])
    color = ramp.outputs["Color"]
    paint = None
    if texture is not None:
        paint = nodes.new("ShaderNodeTexImage")
        paint.label = "UV-authored surface paint"
        paint.image = bpy.data.images.load(str(texture.resolve()), check_existing=True)
        paint.image.pack()
        paint.interpolation = "Closest"
        uv = nodes.new("ShaderNodeTexCoord")
        links.new(uv.outputs["UV"], paint.inputs["Vector"])
        # Neutral midtone paint leaves the normal ramp unchanged. Dark/light
        # painted clusters modulate it without introducing smooth lighting.
        ratio = nodes.new("ShaderNodeVectorMath")
        ratio.operation = "DIVIDE"
        ratio.inputs[1].default_value = tuple(max(.001, c) for c in linear_color(shades[4])[:3])
        links.new(paint.outputs["Color"], ratio.inputs[0])
        multiply = nodes.new("ShaderNodeVectorMath")
        multiply.operation = "MULTIPLY"
        links.new(color, multiply.inputs[0])
        links.new(ratio.outputs["Vector"], multiply.inputs[1])
        color = multiply.outputs["Vector"]
    emission = nodes.new("ShaderNodeEmission")
    links.new(color, emission.inputs["Color"])
    surface = emission.outputs[0]
    if paint is not None:
        transparent = nodes.new("ShaderNodeBsdfTransparent")
        mix = nodes.new("ShaderNodeMixShader")
        links.new(paint.outputs["Alpha"], mix.inputs[0])
        links.new(transparent.outputs[0], mix.inputs[1])
        links.new(surface, mix.inputs[2])
        surface = mix.outputs[0]
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(surface, output.inputs["Surface"])
    return material
