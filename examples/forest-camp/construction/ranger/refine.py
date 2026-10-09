"""A shared head presentation adjustment preserves the source motion phases."""
import argparse,math,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--head-lift',type=float,default=30);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
bpy.ops.wm.open_mainfile(filepath=str(a.source.resolve()),use_scripts=False)
rig=bpy.data.objects['Rig'];head=rig.pose.bones['head'];action=rig.animation_data.action
states=[]
for frame in range(1,bpy.context.scene.frame_end+2):
    bpy.context.scene.frame_set(frame)
    matrices={bone.name:bone.matrix.copy() for bone in rig.pose.bones}
    sole_heights={}
    if action['Source clip'] in ('Walk_Loop', 'Walk_Formal_Loop'):
        deps=bpy.context.evaluated_depsgraph_get()
        for side,index in [('L',1),('R',-1)]:
            obj=bpy.data.objects['Boot '+str(index)].evaluated_get(deps)
            sole_heights[side]=min((obj.matrix_world@v.co).z for v in obj.data.vertices)
    states.append((frame,matrices,sole_heights))
correction=Matrix.Rotation(math.radians(-a.head_lift),4,'X')
previous=None
previous_legs={}
for frame,matrices,sole_heights in states:
    bpy.context.scene.frame_set(frame)
    original=matrices['head']
    posed=correction@original;posed.translation=original.translation
    head.matrix=posed
    q=head.rotation_quaternion
    if previous is not None and q.dot(previous)<0:q.negate()
    previous=q.copy();head.keyframe_insert('rotation_quaternion',frame=frame);head.keyframe_insert('location',frame=frame)
    for side,ground_z in sole_heights.items():
        # Contact IK corrects only penetrating stance shoes; root and swing height stay authored.
        if ground_z>=0:continue
        thigh=rig.pose.bones['thigh.'+side];shin=rig.pose.bones['shin.'+side];foot=rig.pose.bones['foot.'+side];toe=rig.pose.bones['toe.'+side]
        a_point=matrices[thigh.name].translation
        b_point=matrices[shin.name].translation
        c_point=matrices[foot.name].translation
        delta=Vector((0,0,-ground_z))
        target=c_point+delta;axis=(target-a_point).normalized();distance=(target-a_point).length
        upper=thigh.bone.length;lower=shin.bone.length
        along=(upper*upper-lower*lower+distance*distance)/(2*distance)
        bend=b_point-a_point-axis*(b_point-a_point).dot(axis)
        if bend.length<.0001:bend=Vector((0,-1,0))-axis*axis.dot(Vector((0,-1,0)))
        joint=a_point+axis*along+bend.normalized()*math.sqrt(max(0,upper*upper-along*along))
        for bone,old_start,old_end,new_start,new_end in [(thigh,a_point,b_point,a_point,joint),(shin,b_point,c_point,joint,target)]:
            matrix=(old_end-old_start).rotation_difference(new_end-new_start).to_matrix().to_4x4()@matrices[bone.name]
            matrix.translation=new_start;bone.matrix=matrix;bpy.context.view_layer.update()
        for bone in (foot,toe):
            matrix=matrices[bone.name].copy();matrix.translation+=delta;bone.matrix=matrix;bpy.context.view_layer.update()
        for bone in (thigh,shin,foot,toe):
            q=bone.rotation_quaternion
            if bone.name in previous_legs and q.dot(previous_legs[bone.name])<0:q.negate()
            previous_legs[bone.name]=q.copy()
            bone.keyframe_insert('rotation_quaternion',frame=frame);bone.keyframe_insert('location',frame=frame)
action['Presentation refinement']=f'{a.head_lift:g} degree shared head lift; original timing and phase retained'
if action['Source clip'] in ('Walk_Loop', 'Walk_Formal_Loop'):action['Contact refinement']='Analytic two-bone leg IK for penetrating stance soles; source foot orientation, swing height, root and timing retained'
for layer in action.layers:
    for strip in layer.strips:
        for slot in action.slots:
            bag=strip.channelbag(slot)
            if bag:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
bpy.context.scene.frame_set(1);bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(a.output.resolve()),compress=True)
