"""Author a restrained, grounded idle and modeled blink from the neutral rig."""
import argparse
import math
from pathlib import Path
import sys
import bpy
from mathutils import Quaternion, Vector

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
if args.output.exists():
    raise ValueError('Output must be fresh')
bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()), use_scripts=False)
scene = bpy.context.scene
rig = bpy.data.objects['Rig']
base = {bone.name: bone.matrix_basis.copy() for bone in rig.pose.bones}
rig.animation_data_clear()
rig.animation_data_create()
action = bpy.data.actions.new('Relaxed_Idle')
rig.animation_data.action = action
action.use_fake_user = True
action['Motion source'] = 'Authored neutral breathing pose with modeled eyelid blink'
action['Source clip'] = 'Relaxed_Idle'
action['Export frames'] = 16
action['fps'] = 6
action['Loop'] = True
action['Travel speed'] = 0.0
scene.render.fps = 6
scene.frame_start, scene.frame_end = 1, 16
scene.frame_set(1)
deps = bpy.context.evaluated_depsgraph_get()
meshes = [o.evaluated_get(deps) for o in scene.objects if o.type == 'MESH']
rig.location.z -= min((o.matrix_world @ v.co).z for o in meshes for v in o.data.vertices)

# Feet, pelvis and arms retain the neutral pose; the breath expands the chest.
for frame, breath in ((1, 0), (5, 1), (9, .55), (13, .08), (17, 0)):
    scene.frame_set(frame)
    for bone in rig.pose.bones:
        bone.matrix_basis = base[bone.name]
        bone.rotation_mode = 'QUATERNION'
        if bone.name in ('spine', 'chest'):
            bone.rotation_quaternion = (bone.rotation_quaternion @
                Quaternion(Vector((1, 0, 0)), math.radians(-1.2 * breath)))
        bone.keyframe_insert('rotation_quaternion', frame=frame)
        bone.keyframe_insert('location', frame=frame)

for side in (-1, 1):
    eye = bpy.data.objects['Eye ivory ' + str(side)]
    center = sum((v.co.z for v in eye.data.vertices)) / len(eye.data.vertices)
    lid = bpy.data.objects['Upper eyelid ' + str(side)]
    lid.shape_key_add(name='Basis')
    closed = lid.shape_key_add(name='Closed eyelid')
    # Move the existing fitted lid across the same modeled eye socket.
    for vertex in closed.data:
        vertex.co.z = center
    for frame, value in ((1, 0), (6, 0), (7, 1), (8, 0), (17, 0)):
        closed.value = value
        closed.keyframe_insert('value', frame=frame)
        for name in ('Eye ivory ', 'Green iris ', 'Pupil '):
            obj = bpy.data.objects[name + str(side)]
            obj.hide_render = bool(value)
            obj.keyframe_insert('hide_render', frame=frame)

scene.frame_set(1)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), compress=True)
