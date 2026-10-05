"""Measure a baked motion and capture ground contact data inside Blender."""
import argparse
import json
from pathlib import Path
import sys
import bpy

parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()), use_scripts=False)
rig = bpy.data.objects["Rig"]
scene = bpy.context.scene
frames = []
for frame in range(scene.frame_start, scene.frame_end + 2):
    scene.frame_set(frame)
    meshes = [o.evaluated_get(bpy.context.evaluated_depsgraph_get())
              for o in scene.objects if o.type == "MESH"]
    frames.append({"frame": frame,
        "hips": list(rig.matrix_world @ rig.pose.bones["hips"].head),
        "feet": {side: {"ankle": list(rig.matrix_world @ rig.pose.bones["foot." + side].head),
                         "toe": list(rig.matrix_world @ rig.pose.bones["toe." + side].tail)}
                 for side in ["L", "R"]},
        "ground_min": min((o.matrix_world @ v.co).z for o in meshes for v in o.data.vertices),
        "quaternions": {b.name: list(b.rotation_quaternion) for b in rig.pose.bones}})
args.output.write_text(json.dumps({"fps": scene.render.fps, "range": [scene.frame_start, scene.frame_end],
                                  "action": dict(rig.animation_data.action.items()),
                                  "frames": frames}, indent=2) + "\n")
