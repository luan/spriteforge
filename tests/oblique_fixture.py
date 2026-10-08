"""An emission grid and a moving world-normal probe for camera behavior."""
import json
from pathlib import Path
import sys
import bpy

out=Path(sys.argv[sys.argv.index('--')+1])
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/spriteforge/scripts'))
from materials import pixel_material,lit_material

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for x in range(-1,2):
    for y in range(-1,2):
        bpy.ops.mesh.primitive_plane_add(size=1,location=(x,y,0))
        bpy.context.object.data.materials.append(pixel_material('Grid',['506040' if (x+y)%2 else '809060']))
        if (x,y)==(-1,-1):
            image=bpy.data.images.new('Painted cutout',32,2,alpha=True)
            image.pixels=[channel for row in range(2) for column in range(32)
                          for channel in (0,0,1,1 if column<16 else 0)]
            image.filepath_raw=str(out/'cutout.png');image.file_format='PNG';image.save()
            bpy.context.object.data.materials.clear()
            bpy.context.object.data.materials.append(lit_material('Painted cutout','ffffff',out/'cutout.png',paint_strength=1))
        if (x,y)==(0,-1):
            material=bpy.data.materials.new('Native pixel stripes');material.use_nodes=True
            nodes=material.node_tree.nodes;links=material.node_tree.links;nodes.clear()
            geometry=nodes.new('ShaderNodeNewGeometry');separate=nodes.new('ShaderNodeSeparateXYZ')
            phase=nodes.new('ShaderNodeMath');phase.operation='MULTIPLY_ADD';phase.inputs[1].default_value=16;phase.inputs[2].default_value=.5
            floor=nodes.new('ShaderNodeMath');floor.operation='FLOOR'
            parity=nodes.new('ShaderNodeMath');parity.operation='FLOORED_MODULO';parity.inputs[1].default_value=2
            color=nodes.new('ShaderNodeMixRGB');color.inputs[1].default_value=(1,0,0,1);color.inputs[2].default_value=(0,0,1,1)
            emit=nodes.new('ShaderNodeEmission');output=nodes.new('ShaderNodeOutputMaterial')
            for source,socket,destination,input_socket in [(geometry,'Position',separate,0),(separate,'X',phase,0),(phase,0,floor,0),(floor,0,parity,0),(parity,0,color,0),(color,0,emit,'Color'),(emit,0,output,'Surface')]:links.new(source.outputs[socket],destination.inputs[input_socket])
            bpy.context.object.data.materials.clear();bpy.context.object.data.materials.append(material)
bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=32,radius=.24,location=(0,0,1))
probe=bpy.context.object
for face in probe.data.polygons:face.use_smooth=True
material=bpy.data.materials.new('World normal');material.use_nodes=True
nodes=material.node_tree.nodes;links=material.node_tree.links;nodes.clear()
geometry=nodes.new('ShaderNodeNewGeometry')
add=nodes.new('ShaderNodeVectorMath');add.operation='ADD';add.inputs[1].default_value=(1,1,1)
scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs['Scale'].default_value=.5
emit=nodes.new('ShaderNodeEmission');output=nodes.new('ShaderNodeOutputMaterial')
links.new(geometry.outputs['Normal'],add.inputs[0]);links.new(add.outputs['Vector'],scale.inputs[0])
links.new(scale.outputs['Vector'],emit.inputs['Color']);links.new(emit.outputs[0],output.inputs['Surface'])
probe.data.materials.append(material)
for frame,z in ((1,1),(2,2)):
    probe.location.z=z;probe.keyframe_insert(data_path='location',frame=frame)
bpy.context.scene.frame_set(1);bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/'source.blend'))
(out/'settings.json').write_text(json.dumps({'size':[65,65],'pixels_per_unit':16,'anchor':[.5,.5],
    'shear':[-.5,.5],'lighting':'studio','directions':['south'],'frames':[1,2],'outline':None})+'\n')
