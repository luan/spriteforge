"""Extract and rig a UV-mapped anatomical base; run inside Blender."""
import argparse
from pathlib import Path
import sys
import bpy


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    with bpy.data.libraries.load(str(args.source), link=False) as (_, destination):
        destination.objects = ["GEO-body_male_realistic"]
    body = destination.objects[0]
    body.name = "Body"
    bpy.context.scene.collection.objects.link(body)
    body.parent = None
    body.location = body.rotation_euler = (0, 0, 0)
    body.scale = (1, 1, 1)
    for modifier in list(body.modifiers):
        body.modifiers.remove(modifier)
    body.data.materials.clear()
    low = min(v.co.z for v in body.data.vertices)
    scale = 3.76 / (max(v.co.z for v in body.data.vertices) - low)
    for vertex in body.data.vertices:
        vertex.co *= scale
        vertex.co.z -= low * scale
    for face in body.data.polygons:
        face.use_smooth = True
    armature = bpy.data.armatures.new("Humanoid")
    rig = bpy.data.objects.new("Rig", armature)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    def bone(name, head, tail, parent=None, deform=True):
        result = armature.edit_bones.new(name)
        result.head = tuple(v * scale for v in head)
        result.tail = tuple(v * scale for v in tail)
        result.use_deform = deform
        if parent:
            result.parent = armature.edit_bones[parent]

    bone("root", (0, 0, 0), (0, 0, .18), deform=False)
    bone("hips", (0, 0, .81), (0, 0, .96), "root")
    bone("spine", (0, 0, .96), (0, 0, 1.17), "hips")
    bone("chest", (0, 0, 1.17), (0, 0, 1.37), "spine")
    bone("neck", (0, 0, 1.37), (0, -.014, 1.49), "chest")
    bone("head", (0, -.014, 1.49), (0, -.018, 1.68), "neck")
    for sign, side in [(-1, "L"), (1, "R")]:
        bone(f"shoulder.{side}", (0, 0, 1.34), (sign * .16, 0, 1.345), "chest")
        bone(f"upperarm.{side}", (sign * .16, 0, 1.345), (sign * .29, -.005, 1.115), f"shoulder.{side}")
        bone(f"forearm.{side}", (sign * .29, -.005, 1.115), (sign * .38, -.01, .925), f"upperarm.{side}")
        bone(f"hand.{side}", (sign * .38, -.01, .925), (sign * .425, -.016, .82), f"forearm.{side}")
        bone(f"thigh.{side}", (sign * .09, 0, .835), (sign * .158, .012, .46), "hips")
        bone(f"shin.{side}", (sign * .158, .012, .46), (sign * .205, .056, .095), f"thigh.{side}")
        bone(f"foot.{side}", (sign * .205, .056, .095), (sign * .207, -.10, .035), f"shin.{side}")
        bone(f"toe.{side}", (sign * .207, -.10, .035), (sign * .207, -.16, .03), f"foot.{side}")
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    missing = [v.index for v in body.data.vertices if not v.groups]
    if missing:
        raise ValueError(f"unweighted body vertices: {len(missing)}")
    smooth = body.modifiers.new("Surface finish", "SUBSURF")
    smooth.levels = smooth.render_levels = 1
    rig.show_in_front = True
    rig["Source"] = "Blender Studio Human Base Meshes v1.4.1, CC0"
    rig["Authoring"] = "Anatomical base, UVs, and skin weights; add fitted costume, painted materials, and authored motion."
    bpy.context.scene.render.fps = 30
    bpy.context.preferences.filepaths.save_version = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), compress=True)


if __name__ == "__main__":
    main()
