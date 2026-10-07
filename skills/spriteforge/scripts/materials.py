"""Packed UV surface fields for painted and physically lit sprites."""
from pathlib import Path
import bpy


def linear_color(color: str) -> tuple[float, float, float, float]:
    channels = [v / 255 for v in bytes.fromhex(color)]
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in channels) + (1,)


def pixel_material(name: str, shades: list[str] | None = None, texture: Path | None = None) -> bpy.types.Material:
    """Emit painted colors directly; solid accents use the material midtone."""
    if not shades and texture is None:
        raise ValueError("solid materials need a color; textured materials use their image colors")
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    paint = None
    if texture is not None:
        paint = nodes.new("ShaderNodeTexImage")
        paint.label = "UV-authored surface paint"
        paint.image = bpy.data.images.load(str(texture.resolve()), check_existing=True)
        paint.image.pack()
        paint.interpolation = "Closest"
        uv = nodes.new("ShaderNodeTexCoord")
        links.new(uv.outputs["UV"], paint.inputs["Vector"])
    emission = nodes.new("ShaderNodeEmission")
    if paint is not None:
        links.new(paint.outputs["Color"], emission.inputs["Color"])
    else:
        emission.inputs["Color"].default_value = linear_color(shades[len(shades) // 2])
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


def lit_material(name: str, color: str, texture: Path | None = None,
                 roughness: float = .8, metallic: float = 0) -> bpy.types.Material:
    """Continuous material shading; UV fields describe surfaces rather than views."""
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    surface = nodes.get("Principled BSDF")
    surface.inputs["Base Color"].default_value = linear_color(color)
    surface.inputs["Roughness"].default_value = roughness
    surface.inputs["Metallic"].default_value = metallic
    surface.inputs["Specular IOR Level"].default_value = .25
    # A small material-colored fill keeps dark facings readable without banding.
    surface.inputs["Emission Color"].default_value = linear_color(color)
    surface.inputs["Emission Strength"].default_value = .04
    # Live screen-space AO produces dark pinholes on moving native-size meshes.
    # Use geometric shadows; any extra occlusion belongs in stable UV paint.
    if texture is not None:
        paint = nodes.new("ShaderNodeTexImage")
        paint.image = bpy.data.images.load(str(texture.resolve()), check_existing=True)
        paint.image.pack()
        paint.interpolation = "Closest"
        links.new(paint.outputs["Color"], surface.inputs["Base Color"])
        links.new(paint.outputs["Color"], surface.inputs["Emission Color"])
        links.new(paint.outputs["Alpha"], surface.inputs["Alpha"])
    return material
