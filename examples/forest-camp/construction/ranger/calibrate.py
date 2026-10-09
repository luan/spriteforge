"""Calibrate real model geometry to a native height without resampling sprites."""
import argparse
from pathlib import Path
import math
import sys
import bpy
from mathutils import Matrix,Vector

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--skill',type=Path,required=True)
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--height',type=int,default=64)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.output.exists():raise ValueError('Output must be fresh')
sys.path.insert(0,str(args.skill/'scripts'))
from blender_scene import snapshots
from settings import DIRECTIONS

bpy.ops.wm.open_mainfile(filepath=str(args.source),use_scripts=False)
rig=bpy.data.objects['Rig'];scene=bpy.context.scene
evaluated=snapshots(scene,'Mira')
points=[world@vertex.co for mesh,world in evaluated for vertex in mesh.vertices]
heights=[]
for angle in DIRECTIONS.values():
    rotation=Matrix.Rotation(math.radians(angle),3,'Z')
    projected=[(rotation@point).y+.85*point.z for point in points]
    heights.append((max(projected)-min(projected))*24)
factor=(args.height-2)/max(heights)
for mesh,_ in evaluated:bpy.data.meshes.remove(mesh)
identity=Matrix.Identity(4)
for obj in bpy.data.collections['Mira'].objects:
    if any(abs(obj.matrix_world[row][column]-identity[row][column])>1e-5
           for row in range(4) for column in range(4)):
        raise ValueError('Apply object transforms before native model calibration: '+obj.name)
poses={bone.name:bone.matrix_basis.copy() for bone in rig.pose.bones}
for obj in bpy.data.collections['Mira'].objects:
    if obj.type=='MESH':
        for vertex in obj.data.vertices:vertex.co*=factor
        for modifier in obj.modifiers:
            if modifier.type=='SOLIDIFY':modifier.thickness*=factor
            elif modifier.type=='BEVEL':modifier.width*=factor
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
for bone in rig.data.edit_bones:bone.head*=factor;bone.tail*=factor
bpy.ops.object.mode_set(mode='OBJECT')
for name,basis in poses.items():
    basis.translation*=factor;rig.pose.bones[name].matrix_basis=basis
scene['Native model height target']=args.height;scene['Native calibration factor']=factor
bpy.context.view_layer.update()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(args.output),compress=True)
print({'native_precalibration_heights':heights,'geometry_scale':factor,'target':args.height})
