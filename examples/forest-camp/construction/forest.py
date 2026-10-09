"""Author textured conifer boughs, ground transitions and a pond with separate ripples."""
import argparse,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser();p.add_argument('--skill',type=Path,required=True);p.add_argument('--maps',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
if a.output.exists():p.error('output must be fresh')
a.output.parent.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(a.skill.resolve()/'scripts'));from materials import lit_material,pixel_material,linear_color
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.frame_start=1;scene.frame_end=12;scene.render.fps=6
collections={}
for name in ['Pine','Pond','PondBase','PondRipples','Grass','Grass1','Grass2','Grass3','Fern','Flowers']:
    c=bpy.data.collections.new(name);scene.collection.children.link(c);collections[name]=c
materials={}
for name,color,strength in [('foliage','426a35',.45),('bark','805735',.30),('water','396e6c',.90),('soil','987c53',.85),('grass','768d48',.85)]:
    m=lit_material(name,color,a.maps.resolve()/(name+'.png'),roughness=1,paint_strength=strength)
    m.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=0
    for node in m.node_tree.nodes:
        if node.type=='TEX_IMAGE':node.interpolation='Closest' if name in ['grass','soil'] else 'Linear'
    if name in ['soil','water','grass']:
        nodes=m.node_tree.nodes;links=m.node_tree.links
        paint=next(node for node in nodes if node.type=='TEX_IMAGE')
        destinations=[link.to_socket for link in list(links) if link.from_socket==paint.outputs['Color']]
        mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MIX'
        mix.inputs[1].default_value=linear_color('768d48' if name=='grass' else '907958' if name=='soil' else '28696c')
        links.new(paint.outputs['Color'],mix.inputs[2])
        if name in ['soil','grass']:
            mix.inputs[0].default_value=.90 if name=='grass' else .85
            coordinates=nodes.new('ShaderNodeTexCoord');repeat=nodes.new('ShaderNodeVectorMath');repeat.operation='SCALE';repeat.inputs['Scale'].default_value=1
            links.new(coordinates.outputs['UV'],repeat.inputs[0]);links.new(repeat.outputs[0],paint.inputs['Vector'])
        else:
            # Fixed material depth suppresses submerged detail in the deeper centre.
            coordinates=nodes.new('ShaderNodeTexCoord');distance=nodes.new('ShaderNodeVectorMath');distance.operation='DISTANCE';distance.inputs[1].default_value=(.5,.5,0)
            links.new(coordinates.outputs['UV'],distance.inputs[0])
            depth=nodes.new('ShaderNodeMapRange');depth.clamp=True
            for key,value in [('From Min',.17),('From Max',.48),('To Min',.12),('To Max',.65)]:depth.inputs[key].default_value=value
            links.new(distance.outputs['Value'],depth.inputs['Value']);links.new(depth.outputs['Result'],mix.inputs[0])
        for socket in destinations:links.new(mix.outputs[0],socket)
    materials[name]=m
for name in ['grass','soil']:
    # Flat terrain uses the authored full-RGB surface pigment directly.
    materials[name]=pixel_material('Native '+name+' pigment',texture=a.maps.resolve()/(name+'.png'))
    if name=='grass':
        nodes=materials[name].node_tree.nodes;links=materials[name].node_tree.links
        paint=next(node for node in nodes if node.type=='TEX_IMAGE');emission=next(node for node in nodes if node.type=='EMISSION')
        blend=nodes.new('ShaderNodeMixRGB');blend.inputs[0].default_value=.55;blend.inputs[1].default_value=linear_color('6e9548')
        links.new(paint.outputs['Color'],blend.inputs[2]);links.new(blend.outputs['Color'],emission.inputs['Color'])
materials['ripple']=pixel_material('Soft teal ripple',['7daaa3'])
materials['fern']=lit_material('Fern leaflet pigment','6a9943',a.maps.resolve()/'fern.png',roughness=1,paint_strength=.65)
for node in materials['fern'].node_tree.nodes:
    if node.type=='TEX_IMAGE':node.interpolation='Linear'
nodes=materials['fern'].node_tree.nodes;links=materials['fern'].node_tree.links
paint=next(node for node in nodes if node.type=='TEX_IMAGE');destinations=[link.to_socket for link in links if link.from_socket==paint.outputs['Color']]
gain=nodes.new('ShaderNodeMixRGB');gain.blend_type='MULTIPLY';gain.inputs[0].default_value=1;gain.inputs[2].default_value=(1.45,1.6,1.25,1)
links.new(paint.outputs['Color'],gain.inputs[1])
for socket in destinations:links.new(gain.outputs[0],socket)
materials['petal']=lit_material('Violet bellflower','7364a6',roughness=1)
nodes=materials['petal'].node_tree.nodes;links=materials['petal'].node_tree.links
coordinates=nodes.new('ShaderNodeTexCoord');separate=nodes.new('ShaderNodeSeparateXYZ');links.new(coordinates.outputs['UV'],separate.inputs[0])
ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=linear_color('564477');ramp.color_ramp.elements[1].color=linear_color('aaa5d9')
links.new(separate.outputs['Y'],ramp.inputs[0]);links.new(ramp.outputs['Color'],nodes.get('Principled BSDF').inputs['Base Color'])

def mesh(name,vertices,faces,uv,role,collection,smooth=True):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);collections[collection].objects.link(obj);data.materials.append(materials[role])
    layer=data.uv_layers.new(name='Construction pigment')
    for face in data.polygons:
        face.use_smooth=smooth
        for loop in face.loop_indices:layer.data[loop].uv=uv[data.loops[loop].vertex_index]
        if role in ['foliage','bark'] and max(layer.data[i].uv.x for i in face.loop_indices)-min(layer.data[i].uv.x for i in face.loop_indices)>.5:
            for i in face.loop_indices:
                if layer.data[i].uv.x<.5:layer.data[i].uv.x+=1
    return obj

roots={}
def wind(obj,weights,phase,amount):
    obj.shape_key_add(name='Basis');bend=obj.shape_key_add(name='Rooted wind');bend.slider_min=-1;bend.slider_max=1
    for point,t in zip(bend.data,weights):point.co+=Vector((amount*t*t,.025*t*t,0))
    first=math.sin(phase)
    for frame in range(1,14):
        bend.value=first if frame==13 else math.sin(math.tau*(frame-1)/12+phase)
        bend.keyframe_insert('value',frame=frame)
    action=obj.data.shape_keys.animation_data.action;action['Loop']=True;action['Export frames']=12;action['fps']=6
    for layer in action.layers:
        for strip in layer.strips:
            for slot in action.slots:
                bag=strip.channelbag(slot)
                if bag:
                    for curve in bag.fcurves:
                        for key in curve.keyframe_points:key.interpolation='CONSTANT'
    roots[obj.name]=[tuple(v.co) for v,t in zip(obj.data.vertices,weights) if t==0]

def tube(name,points,radii,collection,phase=None,amount=.08):
    verts=[];uv=[];faces=[];weights=[];n=12
    for j,point in enumerate(points):
        axis=(points[min(j+1,len(points)-1)]-points[max(0,j-1)]).normalized()
        perpendicular=axis.cross(Vector((0,1,0)))
        if perpendicular.length<.01:perpendicular=axis.cross(Vector((1,0,0)))
        perpendicular.normalize();other=axis.cross(perpendicular).normalized()
        for i in range(n):
            angle=math.tau*i/n
            verts.append(point+radii[j]*(perpendicular*math.cos(angle)+other*math.sin(angle)))
            uv.append((i/n,j/(len(points)-1)));weights.append(j/(len(points)-1))
            if j:
                k=(j-1)*n+i;faces.append((k,(j-1)*n+(i+1)%n,j*n+(i+1)%n,j*n+i))
    faces += [tuple(reversed(range(n))),tuple((len(points)-1)*n+i for i in range(n))]
    obj=mesh(name,verts,faces,uv,'bark',collection)
    if phase is not None:wind(obj,weights,phase,amount)
    return obj

tube('Tapered pine trunk',[Vector((.025*math.sin(i*.7),.02*math.sin(i*.9),i*5.05/10)) for i in range(11)],
     [.20*(1-i/11)**1.25+.014 for i in range(11)],'Pine')
for i in range(4):
    az=math.tau*i/4+.3;radial=Vector((math.cos(az),math.sin(az),0))
    tube('Grounded root '+str(i),[radial*.08+Vector((0,0,.17)),radial*.30+Vector((0,0,.045)),radial*.51+Vector((0,0,.02))],[.085,.06,.015],'Pine')

# Whorls carry individual curved, folded needle sprays attached to actual branches.
for tier,(height,reach,drop,count) in enumerate([(1.92,1.12,.32,10),(2.85,.96,.27,9),(3.72,.75,.22,8),(4.50,.48,.10,7)]):
    for bough in range(count):
        az=math.tau*bough/count+tier*.43;radial=Vector((math.cos(az),math.sin(az),0))
        origin=radial*.10+Vector((0,0,height+.06*math.sin(bough*1.7)))
        end=origin+radial*reach+Vector((0,0,-drop));axis=(end-origin).normalized()
        cross=Vector((-math.sin(az),math.cos(az),0));normal=axis.cross(cross).normalized()
        phase=tier*.17+bough*.045
        tube(f'Pine branch {tier}-{bough}',[origin,origin+(end-origin)*.48+Vector((0,0,.08)),end],[.045,.032,.009],'Pine',phase)
        verts=[];uv=[];faces=[];weights=[];rows=12;n=12
        for j in range(rows+1):
            t=j/rows;center=origin+(end-origin)*t+Vector((0,0,.13*math.sin(math.pi*t)))
            width=.018+(.31-.045*tier)*math.sin(math.pi*t)**.75
            thickness=.018+.11*math.sin(math.pi*t)
            for i in range(n):
                angle=math.tau*i/n;fold=1+.09*math.cos(4*angle+math.pi*3*t)
                verts.append(center+cross*(width*math.cos(angle)*fold)+normal*(thickness*math.sin(angle)))
                uv.append((i/n,t));weights.append(t)
                if j:
                    k=(j-1)*n+i;faces.append((k,(j-1)*n+(i+1)%n,j*n+(i+1)%n,j*n+i))
        faces += [tuple(reversed(range(n))),tuple(rows*n+i for i in range(n))]
        obj=mesh(f'Folded needle spray {tier}-{bough}',verts,faces,uv,'foliage','Pine');wind(obj,weights,phase,.08)
for i in range(4):
    az=math.tau*i/4;origin=Vector((0,0,4.46));end=Vector((.20*math.cos(az),.20*math.sin(az),5.18))
    # Tapered leading shoot, using the same constructed branch/needle vocabulary.
    verts=[];uv=[];faces=[];weights=[];n=12
    for j in range(9):
        t=j/8;center=origin.lerp(end,t);radius=.014+.13*math.sin(math.pi*t)**.8
        for k in range(n):
            angle=math.tau*k/n;verts.append(center+Vector((radius*math.cos(angle),radius*math.sin(angle),0)));uv.append((k/n,t));weights.append(t)
            if j:
                a0=(j-1)*n+k;faces.append((a0,(j-1)*n+(k+1)%n,j*n+(k+1)%n,j*n+k))
    obj=mesh('Leading needle shoot '+str(i),verts,faces,uv,'foliage','Pine');wind(obj,weights,.25,.08)

q=64/24/2
low=[(-q,-.72),(-1.,-.69),(-.66,-.77),(-.30,-.71),(.12,-.75),(.53,-.69),(.96,-.76),(q,-.72)]
high=[(q,.72),(.96,.77),(.56,.70),(.14,.75),(-.28,.68),(-.63,.74),(-1.,.70),(-q,.72)]
path_shapes={'Dirt straight':low+high,
 'Dirt corner':[(-q,-.72),(.22,-.72),(.58,-.59),(.74,-.32),(.72,q),(-.72,q),(-.69,.79),(-.83,.73),(-q,.72)],
 'Dirt cross':[(-q,-.72),(-.72,-.72),(-.72,-q),(.72,-q),(.72,-.72),(q,-.72),(q,.72),(.72,.72),(.72,q),(-.72,q),(-.72,.72),(-q,.72)]}
ground_vertices=[(-q,-q,0),(q,-q,0),(q,q,0),(-q,q,0)]
ground_uv=[(0,.5),(.5,.5),(.5,1),(0,1)]
mesh('Full opaque grass',ground_vertices,[(0,1,2,3)],ground_uv,'grass','Grass',False)
for index,(u,v) in enumerate([(.5,0),(0,-.5),(.5,-.5)],1):
    mesh('Connected terrain field '+str(index),ground_vertices,[(0,1,2,3)],[(x+u,y+v) for x,y in ground_uv],'grass','Grass'+str(index),False)
terrain_exports=[]
for collection,shape in path_shapes.items():
    for orientation in range(4):
        name=collection+' '+str(orientation);c=bpy.data.collections.new(name);scene.collection.children.link(c);collections[name]=c
        mesh('Matching grass '+name,ground_vertices,[(0,1,2,3)],ground_uv,'grass',name,False)
        angle=math.pi/2*orientation;cosine=math.cos(angle);sine=math.sin(angle)
        rotated=[(x*cosine-y*sine,x*sine+y*cosine) for x,y in shape]
        verts=[(x,y,.001) for x,y in rotated]
        obj=mesh(name,verts,[tuple(range(len(verts)))],[((x+q)/(4*q),(y+q)/(4*q)+.5) for x,y in rotated],'soil',name,False);obj.visible_shadow=False
        terrain_exports.append((collection.lower().replace(' ','-')+'-'+str(orientation),name,[64,64],[.5,.5],[1],None))
alternate=bpy.data.collections.new('Dirt straight alternate field');scene.collection.children.link(alternate);collections[alternate.name]=alternate
for source in collections['Dirt straight 0'].objects:
    obj=source.copy();obj.data=source.data.copy();alternate.objects.link(obj)
    for coordinate in obj.data.uv_layers.active.data:coordinate.uv.x+=.5
terrain_exports.append(('dirt-straight-alternate',alternate.name,[64,64],[.5,.5],[1],None))

# Static bank/depth; the pond's water appearance does not swim between frames.
n=96;inner=[];outer=[]
for i in range(n):
    az=math.tau*i/n;r=1.64+.15*math.sin(az*3+.5)+.10*math.sin(az*5-.4)
    inner.append(Vector((r*math.cos(az),r*.78*math.sin(az),.012)))
    width=.18+.035*math.sin(az*4)
    outer.append(Vector(((r+width)*math.cos(az),(r+width)*.78*math.sin(az),.010)))
verts=[Vector((0,0,.012))]+inner
obj=mesh('Fixed pond depth',verts,[(0,i+1,(i+1)%n+1) for i in range(n+1-1)],
         [(p.x/3.8+.5,p.y/3.1+.5) for p in verts],'water','PondBase',False);obj.visible_shadow=False
verts=inner+outer;faces=[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
obj=mesh('Compacted pond bank',verts,faces,[(p.x/(2*q)+.5,p.y/(2*q)+.5) for p in verts],'soil','PondBase',False);obj.visible_shadow=False
for index,(y,length,phase) in enumerate([(-.70,.60,.0),(-.22,.88,.8),(.35,.69,1.7),(.76,.40,2.5)]):
    verts=[];uv=[];faces=[]
    for i in range(25):
        t=i/24;x=(t-.5)*length*2;cy=y+.15*math.sin(math.pi*t)+.018*math.sin(t*math.tau*2)
        for side in (-1,1):
            verts.append((x,cy+side*.031*math.sin(math.pi*t)**.2,.016));uv.append((t,(side+1)/2))
        if i:faces.append((2*i-2,2*i-1,2*i+1,2*i))
    obj=mesh('Pond ripple '+str(index),verts,faces,uv,'ripple','PondRipples',False);obj.visible_shadow=False
    wind(obj,[1]*len(verts),phase,.055)

# Pinnate fronds: each leaflet has a raised midrib and follows its curled stem.
for frond in range(9):
    az=math.tau*frond/9+.14;radial=Vector((math.cos(az),math.sin(az),0));cross=Vector((-math.sin(az),math.cos(az),0))
    reach=.62+.12*math.sin(frond*1.8);height=.47+.13*math.cos(frond*1.3)
    def center(t):return radial*(.08+reach*t)+Vector((0,0,.03+height*math.sin(math.pi*t*.78)))
    verts=[];faces=[];uv=[];weights=[]
    for leaf in range(7):
        t=.15+leaf*.115;start=center(t);length=.17*math.sin(math.pi*t)**.65+.02
        for side in (-1,1):
            tip=start+cross*(side*length)+radial*.12+Vector((0,0,.025))
            lateral=(tip-start).cross(Vector((0,0,1))).normalized()*.035
            ridge=start.lerp(tip,.48)+Vector((0,0,.023));base=len(verts)
            verts += [start,start.lerp(tip,.4)+lateral,tip,start.lerp(tip,.4)-lateral,ridge]
            uv += [(.5,0),(0,.4),(.5,1),(1,.4),(.5,.45)];weights += [t]*5
            faces += [(base,base+1,base+4),(base+1,base+2,base+4),(base+2,base+3,base+4),(base+3,base,base+4)]
    obj=mesh('Pinnate fern frond '+str(frond),verts,faces,uv,'fern','Fern');wind(obj,weights,frond*.12,.027)
    verts=[];uv=[];faces=[];weights=[]
    for i in range(17):
        t=i/16;p0=center(t)
        for side in (-1,1):verts.append(p0+cross*side*.012);uv.append(((side+1)/2,t));weights.append(t)
        if i:faces.append((i*2-2,i*2-1,i*2+1,i*2))
    obj=mesh('Curled green fern rachis '+str(frond),verts,faces,uv,'fern','Fern');wind(obj,weights,frond*.12,.027)

for flower,(x,y,h) in enumerate([(-.18,.04,.54),(.12,-.14,.43),(.22,.19,.69),(-.24,-.16,.35),(.03,.03,.77)]):
    tip=Vector((x,y,h));stem_start=Vector((x*.4,y*.4,0));verts=[];faces=[];uv=[];weights=[]
    for i in range(13):
        t=i/12;p0=stem_start.lerp(tip,t)+Vector((.035*math.sin(math.pi*t),0,0))
        for side in (-1,1):verts.append(p0+Vector((side*.012,0,0)));uv.append(((side+1)/2,t));weights.append(t)
        if i:faces.append((i*2-2,i*2-1,i*2+1,i*2))
    obj=mesh('Bellflower stem '+str(flower),verts,faces,uv,'foliage','Flowers');wind(obj,weights,flower*.08,.018)
    for petal in range(5):
        az=math.tau*petal/5;radial=Vector((math.cos(az),math.sin(az),0));side=Vector((-math.sin(az),math.cos(az),0))
        verts=[tip+Vector((0,0,-.05)),tip+radial*.09+side*.055,tip+radial*.145+Vector((0,0,-.025)),tip+radial*.09-side*.055,tip+radial*.073+Vector((0,0,.015))]
        obj=mesh(f'Folded bell petal {flower}-{petal}',verts,[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],[(.5,0),(0,.5),(.5,1),(1,.5),(.5,.5)],'petal','Flowers');wind(obj,[1]*5,flower*.08,.018)
    for side in (-1,1):
        start=stem_start.lerp(tip,.38);end=start+Vector((side*.15,.025,.13));mid=start.lerp(end,.5)
        verts=[start,mid+Vector((0,.035,.018)),end,mid-Vector((0,.035,-.018))]
        obj=mesh(f'Bellflower leaf {flower}-{side}',verts,[(0,1,2),(0,2,3)],[(.5,0),(0,.5),(.5,1),(1,.5)],'foliage','Flowers');wind(obj,[.38]*4,flower*.08,.018)

scene['Construction']='Independent modeled pine with rooted boughs, compatible dirt masks, fixed-depth pond with separate ripple meshes'
scene['Texture origin']='Original UV material atlas; no rendered scene projection'
scene['Pixel density']=24;scene['Closing source frame']=13
for name in ['PondBase','PondRipples']:
    for obj in collections[name].objects:collections['Pond'].objects.link(obj)
scene.frame_set(1)
for image in bpy.data.images:
    if image.source=='FILE':image.pack()
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(a.output.resolve()),compress=True)
base={'pixels_per_unit':24,'directions':['south'],'fps':6,'pivot':[0,0,0],'shear':[0,.85],
      'light':[-.5,-.65,1],'outline':None,'shading':'preserve','supersample':1,'cluster_materials':[],'lighting':'studio'}
exports=[('pine','Pine',[144,144],[.5,.80],list(range(1,13)),'243223'),
         ('pond','Pond',[128,128],[.5,.5],list(range(1,13)),None),
         ('pond-base','PondBase',[128,128],[.5,.5],[1],None),
         ('pond-ripples','PondRipples',[128,128],[.5,.5],list(range(1,13)),None),
         ('fern','Fern',[80,80],[.5,.65],list(range(1,13)),None),
         ('flowers','Flowers',[64,64],[.5,.70],list(range(1,13)),'283323'),
         ('grass','Grass',[64,64],[.5,.5],[1],None)]+terrain_exports
exports += [('grass-'+str(index),'Grass'+str(index),[64,64],[.5,.5],[1],None) for index in range(1,4)]
for name,collection,size,anchor,frames,outline in exports:
    cfg=base|{'collection':collection,'size':size,'anchor':anchor,'frames':frames,'outline':outline}
    if name.startswith('grass') or name.startswith('dirt-'):cfg['opaque']=True
    (a.output.parent/(name+'.json')).write_text(json.dumps(cfg,indent=2)+'\n')
(a.output.parent/'exports.json').write_text(json.dumps([v[0] for v in exports],indent=2)+'\n')
(a.output.parent/'wind-roots.json').write_text(json.dumps(roots,indent=2)+'\n')
print('Authored',sum(len(o.data.polygons) for o in scene.objects if o.type=='MESH'),'textured faces across five independent entities')
