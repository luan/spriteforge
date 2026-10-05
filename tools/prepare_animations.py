"""Extract the CC0 animation rig and actions from the creator's GLB in Blender."""
import argparse
from pathlib import Path
import sys
import bpy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--root-motion", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.context.scene.render.fps = 30
    bpy.ops.import_scene.gltf(filepath=str(args.source.resolve()))
    rigs = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    if len(rigs) != 1:
        raise ValueError("expected one animation armature")
    rig = rigs[0]
    rig.name = "MotionLibrary"
    actions = {a.name: a for a in bpy.data.actions}
    before = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=str(args.root_motion.resolve()))
    moving = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE" and o != rig)
    for action in set(bpy.data.actions) - before:
        name = action.name.removesuffix(".001")
        moving.animation_data.action = action
        moving.animation_data.action_slot = action.slots[0]
        start, end = action.frame_range
        bpy.context.scene.frame_set(round(start))
        first = moving.matrix_world @ moving.pose.bones["root"].head
        bpy.context.scene.frame_set(round(end))
        last = moving.matrix_world @ moving.pose.bones["root"].head
        duration = (end - start) / 30
        delta = last - first
        actions[name]["Source speed"] = (delta.x ** 2 + delta.y ** 2) ** .5 / duration if duration else 0
        bpy.data.actions.remove(action)
    for obj in list(bpy.context.scene.objects):
        if obj != rig:
            bpy.data.objects.remove(obj, do_unlink=True)
    if rig.animation_data:
        for track in list(rig.animation_data.nla_tracks):
            rig.animation_data.nla_tracks.remove(track)
        rig.animation_data.action = None
    for action in bpy.data.actions:
        action.use_fake_user = True
        action["Source fps"] = 30
        action["Loop"] = action.name.endswith("_Loop") or action.name == "Sword_Idle"
    rig["Source"] = "Quaternius Universal Animation Library Standard v3.0, CC0"
    bpy.data.orphans_purge(do_recursive=True)
    bpy.context.preferences.filepaths.save_version = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), compress=True)
    print({"bones": len(rig.data.bones), "actions": [a.name for a in bpy.data.actions]})


if __name__ == "__main__":
    main()
