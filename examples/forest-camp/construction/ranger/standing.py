"""Pose the modeled character for a neutral native art review; run in Blender."""
import argparse
from pathlib import Path
import math
import sys
import bpy
from mathutils import Matrix,Vector

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.output.exists():raise ValueError('Output must be fresh')
bpy.ops.wm.open_mainfile(filepath=str(args.source),use_scripts=False)
rig=bpy.data.objects['Rig'];rig.animation_data_clear()
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
for side,direction in [('L',1),('R',-1)]:
    for name,axis in [('upperarm',Vector((direction*.16,0,-1))),('forearm',Vector((direction*.05,-.14,-1)))]:
        bone=rig.pose.bones[name+'.'+side]
        matrix=(bone.tail-bone.head).rotation_difference(axis).to_matrix().to_4x4()@bone.matrix
        matrix.translation=bone.head.copy();bone.matrix=matrix
        bpy.context.view_layer.update()
head=rig.pose.bones['head']
matrix=Matrix.Rotation(math.radians(-25),4,'X')@head.matrix
matrix.translation=head.head.copy();head.matrix=matrix
bpy.context.view_layer.update()
scene=bpy.context.scene;scene.frame_start=scene.frame_end=1
scene['Art review']='Neutral standing pose; actual rig and weighted mesh surfaces'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(args.output),compress=True)
