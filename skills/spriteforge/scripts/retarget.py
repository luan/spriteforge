"""Bake the bundled CC0 motions onto an authored humanoid; run inside Blender."""
import argparse
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Matrix

MAPPING = {"hips": "pelvis", "spine": "spine_01", "chest": "spine_03",
           "neck": "neck_01", "head": "Head"}
for side, suffix in [("L", "l"), ("R", "r")]:
    MAPPING.update({f"{target}.{side}": f"{source}_{suffix}" for target, source in [
        ("shoulder", "clavicle"), ("upperarm", "upperarm"), ("forearm", "lowerarm"),
        ("hand", "hand"), ("thigh", "thigh"), ("shin", "calf"),
        ("foot", "foot"), ("toe", "ball")]})


def bake(target, motion, source_action, mapping, fps):
    missing = [name for name, source in mapping.items()
               if name not in target.pose.bones or source not in motion.pose.bones]
    if missing:
        raise ValueError(f"bone map contains missing bones: {missing}")
    # Preserve roll while using the source's posed limb directions. Transferring
    # local rotations directly would apply a T-pose clip to an A-pose twice.
    offsets = {}
    for name, source in mapping.items():
        src = motion.data.bones[source]
        dst = target.data.bones[name]
        source_axis = (src.tail_local - src.head_local).normalized()
        target_axis = (dst.tail_local - dst.head_local).normalized()
        align = source_axis.rotation_difference(target_axis)
        offsets[name] = src.matrix_local.to_quaternion().inverted() @ align.inverted() @ dst.matrix_local.to_quaternion()
    hips = [name for name, source in mapping.items() if source == "pelvis"]
    if len(hips) != 1:
        raise ValueError("bone map must map exactly one target hip bone to pelvis")
    hip_name = hips[0]
    scale = target.data.bones[hip_name].head_local.z / motion.data.bones["pelvis"].head_local.z
    start, end = source_action.frame_range
    source_fps = source_action.get("Source fps", 30)
    loop = source_action.get("Loop", source_action.name.endswith("_Loop"))
    count = max(1, round((end - start) * fps / source_fps) + (0 if loop else 1))
    motion.animation_data_create()
    motion.animation_data.action = source_action
    motion.animation_data.action_slot = source_action.slots[0]
    target.animation_data_clear()
    target.animation_data_create()
    action = bpy.data.actions.new(source_action.name + "_retargeted")
    action.use_fake_user = True
    action["Motion source"] = "Quaternius Universal Animation Library Standard v3.0, CC0"
    action["Source clip"] = source_action.name
    action["Export frames"] = count
    action["fps"] = fps
    action["Loop"] = loop
    action["Travel speed"] = source_action.get("Source speed", 0) * scale
    target.animation_data.action = action
    for bone in target.pose.bones:
        bone.rotation_mode = "QUATERNION"
        bone.matrix_basis = Matrix.Identity(4)
        for constraint in bone.constraints:
            constraint.mute = True
    previous = {}
    for frame in range(-1, count + (1 if loop else 0)):
        if frame == -1:
            motion.animation_data.action = None
            for bone in motion.pose.bones:
                bone.matrix_basis = Matrix.Identity(4)
            bpy.context.view_layer.update()
        else:
            motion.animation_data.action = source_action
            motion.animation_data.action_slot = source_action.slots[0]
            # A rounded sprite sample count must still include the exact closing
            # pose or one-shot endpoint when the source duration is indivisible.
            intervals = count if loop else max(1, count - 1)
            source_frame = start + (end - start) * frame / intervals
            bpy.context.scene.frame_set(math.floor(source_frame), subframe=source_frame % 1)
        posed = {}
        for bone in sorted(target.pose.bones, key=lambda b: len(b.parent_recursive)):
            rest = bone.bone.matrix_local
            parent = bone.parent
            inherited = (posed[parent.name] @ parent.bone.matrix_local.inverted() @ rest
                         if parent else rest.copy())
            if bone.name in mapping:
                src = motion.pose.bones[mapping[bone.name]]
                rotation = src.matrix.to_quaternion() @ offsets[bone.name]
                desired = rotation.to_matrix().to_4x4()
                desired.translation = inherited.translation
                if bone.name == hip_name:
                    desired.translation += (src.head - src.bone.head_local) * scale
                basis = inherited.inverted() @ desired
                quaternion = basis.to_quaternion()
                if bone.name in previous and quaternion.dot(previous[bone.name]) < 0:
                    quaternion.negate()
                previous[bone.name] = quaternion.copy()
                bone.rotation_quaternion = quaternion
                bone.location = basis.translation
                if frame >= 0:
                    bone.keyframe_insert("rotation_quaternion", frame=frame + 1)
                    bone.keyframe_insert("location", frame=frame + 1)
                posed[bone.name] = desired
            else:
                posed[bone.name] = inherited
        if frame == -1:
            bpy.context.view_layer.update()
            meshes = [o.evaluated_get(bpy.context.evaluated_depsgraph_get())
                      for o in bpy.context.scene.objects if o.type == "MESH"
                      and (o in target.children_recursive or any(m.type == "ARMATURE" and m.object == target
                                                              for m in o.modifiers))]
            if not meshes:
                raise ValueError("target rig has no attached or weighted character meshes")
            # One reference-pose adjustment, shared by all clips. Per-frame
            # recentering would erase the authored weight shift and jump height.
            ground_offset = -min((o.matrix_world @ v.co).z for o in meshes for v in o.data.vertices)
            target.location.z += ground_offset
            action["Ground offset"] = ground_offset
    for layer in action.layers:
        for strip in layer.strips:
            for slot in action.slots:
                bag = strip.channelbag(slot)
                if bag:
                    for curve in bag.fcurves:
                        for key in curve.keyframe_points:
                            key.interpolation = "LINEAR"
    return action, count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--action", default="Walk_Loop")
    parser.add_argument("--rig", default="Rig")
    parser.add_argument("--bone-map", type=Path)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--library", type=Path, default=Path(__file__).resolve().parents[1] / "assets/animations.blend")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    if args.output.exists() or args.fps <= 0:
        raise ValueError("output must be fresh and fps must be positive")
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()), use_scripts=False)
    target = bpy.data.objects.get(args.rig)
    if target is None or target.type != "ARMATURE":
        raise ValueError(f"missing target armature: {args.rig}")
    basis = target.matrix_world.to_3x3()
    if any(abs(basis[row][column] - (row == column)) > 1e-5
           for row in range(3) for column in range(3)):
        raise ValueError("apply target armature rotation and scale before retargeting; face -Y")
    with bpy.data.libraries.load(str(args.library), link=False) as (available, loaded):
        if args.action not in available.actions:
            raise ValueError(f"unknown clip {args.action!r}; available: {available.actions}")
        loaded.objects = ["MotionLibrary"]
        loaded.actions = [args.action]
    motion = loaded.objects[0]
    bpy.context.scene.collection.objects.link(motion)
    mapping = json.loads(args.bone_map.read_text()) if args.bone_map else MAPPING
    action, count = bake(target, motion, loaded.actions[0], mapping, args.fps)
    bpy.data.objects.remove(motion, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = args.fps
    scene.frame_start, scene.frame_end = 1, count
    scene.frame_set(1)
    bpy.context.preferences.filepaths.save_version = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), compress=True)
    print(json.dumps({"action": action.name, "frames": count, "fps": args.fps,
                      "closing_pose": count + 1 if action["Loop"] else None,
                      "source_clip": args.action}))


if __name__ == "__main__":
    main()
