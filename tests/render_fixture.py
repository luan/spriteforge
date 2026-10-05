"""Source fixtures for public renderer behavior; run inside Blender."""
import json
from pathlib import Path
import sys
import bpy

directory = Path(sys.argv[sys.argv.index("--") + 1])
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/spriteforge/scripts"))
from materials import pixel_material

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
mesh = bpy.data.meshes.new("Two material regions")
mesh.from_pydata([(-2, -2, 0), (0, -2, 0), (0, 2, 0), (-2, 2, 0),
                 (2, -2, 0), (2, 2, 0)], [], [(0, 1, 2, 3), (1, 4, 5, 2)])
obj = bpy.data.objects.new("Painted surface", mesh)
bpy.context.scene.collection.objects.link(obj)
palette = {"red": ["220000", "440000", "660000", "880000", "aa0000", "cc0000", "ee0000"],
           "blue": ["000022", "000044", "000066", "000088", "0000aa", "0000cc", "0000ee"]}
for name in ("red", "blue"):
    material = pixel_material(name, palette[name], directory / f"{name}.png")
    mesh.materials.append(material)
    nodes, links = material.node_tree.nodes, material.node_tree.links
    paint = next(n for n in nodes if n.type == "TEX_IMAGE")
    uv_source = paint.inputs["Vector"].links[0].from_socket
    offset = nodes.new("ShaderNodeVectorMath")
    offset.operation = "ADD"
    links.new(uv_source, offset.inputs[0])
    links.new(offset.outputs["Vector"], paint.inputs["Vector"])
    offset.inputs[1].default_value = (0, 0, 0)
    offset.inputs[1].keyframe_insert("default_value", frame=1)
    offset.inputs[1].default_value = (.5, 0, 0)
    offset.inputs[1].keyframe_insert("default_value", frame=2)
mesh.polygons[1].material_index = 1
uv = mesh.uv_layers.new(name="UVMap")
for polygon in mesh.polygons:
    for loop, coordinate in zip(polygon.loop_indices, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[loop].uv = coordinate
bpy.context.preferences.filepaths.save_version = 0
bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(directory / "source.blend"))
(directory / "settings.json").write_text(json.dumps({"size": [64, 64], "pixels_per_unit": 8,
    "palette": palette, "anchor": [.5, .5], "outline": None, "directions": ["south"], "frames": [1, 2]}))
