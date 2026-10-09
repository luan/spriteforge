"""Build Mira only from the installed Spriteforge anatomical base and this design."""
import argparse
import json
import math
from pathlib import Path
import sys
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

args = argparse.ArgumentParser()
args.add_argument('--skill', type=Path, required=True)
args.add_argument('--output', type=Path, required=True)
opts = args.parse_args(sys.argv[sys.argv.index('--') + 1:])
ROOT = opts.output.resolve()
sys.path.insert(0, str(opts.skill / 'scripts'))
from materials import pixel_material
from style import soft_ramp

bpy.ops.wm.open_mainfile(filepath=str(opts.skill / 'assets/humanoid.blend'), use_scripts=False)
bpy.ops.object.select_all(action='DESELECT')
scene = bpy.context.scene
rig = bpy.data.objects['Rig']
body = bpy.data.objects['Body']
scene.render.fps = 30
scene.frame_start = scene.frame_end = 1
palette = json.loads((opts.skill / 'assets/style.json').read_text())['palette']
palette.update({
    'skin': soft_ramp(['67443b','a36950','d39a73','f0c7a1']),
    'sage': soft_ramp(['303b2d','566447','859477','b0bea0']),
    'cream': soft_ramp(['665c46','9a8969','cfbd94','eee1bb']),
    'hair': soft_ramp(['351c18','713620','ac5b2c','d18c4d']),
    'leather': soft_ramp(['2a1f19','573923','8b633b','b48b59']),
    'brass': soft_ramp(['594127','94723e','cbaa60','eddb91']),
    'eye': soft_ramp(['182721','2f4939','4b6952','819473']),
    'ink': ['242220'] * 7,
})
materials = {name: pixel_material(name, colors, ROOT / 'textures' / (name + '.png') if (ROOT / 'textures' / (name + '.png')).exists() else None) for name, colors in palette.items()}
materials['facial-mark']=pixel_material('facial-mark',[palette['hair'][0]])
def surface_material(role, surface):
    key=role+'/'+surface
    if key not in materials:
        texture=ROOT/'textures'/(surface+'.png')
        if not texture.exists():texture=ROOT/'textures'/(role+'.png')
        materials[key]=pixel_material(role,palette[role],texture if texture.exists() else None)
    return materials[key]
collection = bpy.data.collections.new('Mira')
scene.collection.children.link(collection)
for obj in (body, rig):
    for old in list(obj.users_collection): old.objects.unlink(obj)
    collection.objects.link(obj)

def adapted(p):
    p = p.copy()
    oldz = p.z
    if oldz < 1.802: p.z = oldz * .94
    elif oldz < 3.048: p.z = 1.694 + (oldz - 1.802) * 1.04
    else: p.z = 2.99 + (oldz - 3.048) * 1.42
    head = max(0, min(1, (oldz - 3.08) / .23))
    p.x *= 1.08 + .42 * head
    p.y *= 1.10 + .38 * head
    return p

for vertex in body.data.vertices: vertex.co = adapted(vertex.co)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for bone in rig.data.edit_bones:
    bone.head = adapted(bone.head)
    bone.tail = adapted(bone.tail)
bpy.ops.object.mode_set(mode='OBJECT')
rig.select_set(False)
for poly in body.data.polygons: poly.use_smooth = True
body.data.materials.clear()
body.data.materials.append(materials['skin'])
for mod in body.modifiers:
    if mod.type == 'SUBSURF': mod.levels = mod.render_levels = 1

def uv_cylinder(obj):
    uv = obj.data.uv_layers.get('UVMap') or obj.data.uv_layers.new(name='UVMap')
    zs = [v.co.z for v in obj.data.vertices]
    low, high = min(zs), max(zs)
    center_x=(min(v.co.x for v in obj.data.vertices)+max(v.co.x for v in obj.data.vertices))/2
    center_y=(min(v.co.y for v in obj.data.vertices)+max(v.co.y for v in obj.data.vertices))/2
    for face in obj.data.polygons:
        for li in face.loop_indices:
            p = obj.data.vertices[obj.data.loops[li].vertex_index].co
            uv.data[li].uv = ((math.atan2(p.x-center_x, -(p.y-center_y)) / (2 * math.pi)) % 1, (p.z-low) / max(.001, high-low))
        values=[uv.data[li].uv.x for li in face.loop_indices]
        if max(values)-min(values)>.5:
            for li in face.loop_indices:
                if uv.data[li].uv.x<.5:uv.data[li].uv.x+=1

def fold_distance(point, path):
    position=Vector((point.x,point.z))
    distance=float('inf')
    for start,end in zip(path,path[1:]):
        a,b=Vector(start),Vector(end)
        segment=b-a
        t=max(0,min(1,(position-a).dot(segment)/segment.length_squared))
        distance=min(distance,(position-(a+t*segment)).length)
    return distance

def cloth_folds(obj):
    # Shoulder and waist tension shape the cloth independently of body muscles.
    folds=[([(-.36,2.79),(-.16,2.52),(-.29,2.24)],.085),
           ([(.33,2.74),(.17,2.41),(.30,2.22)],.070),
           ([(-.30,2.25),(-.16,2.10),(-.26,1.91)],.055),
           ([(.24,2.29),(.12,2.08),(.22,1.91)],.070)]
    for vertex in obj.data.vertices:
        p=vertex.co
        if p.y>=-.10 or not 1.88<p.z<2.9:continue
        edge=min(1,(p.z-1.88)/.12,(2.9-p.z)/.12)
        displacement=sum(amplitude*(math.exp(-(fold_distance(p,path)/.085)**2)
                                  -.75*math.exp(-(fold_distance(p,path)/.028)**2))
                         for path,amplitude in folds)
        p.y-=displacement*edge
    obj.data.update()

def clipped(name, planes, material, offset=.02, shell=.015):
    obj = body.copy()
    obj.data = body.data.copy()
    obj.name = name
    collection.objects.link(obj)
    bm = bmesh.new(); bm.from_mesh(obj.data)
    for point, normal in planes:
        bmesh.ops.bisect_plane(bm, geom=list(bm.verts)+list(bm.edges)+list(bm.faces), plane_co=point, plane_no=normal, clear_outer=True, clear_inner=False, dist=.000001)
    if material in ('sage','cream'):
        # Cloth spans the underlying muscles; boundary loops retain their cut.
        interior=[v for v in bm.verts if not v.is_boundary]
        for _ in range(14):
            positions={v:sum((e.other_vert(v).co for e in v.link_edges),Vector())/len(v.link_edges) for v in interior if v.link_edges}
            for v,p in positions.items():v.co=v.co.lerp(p,.45)
        bm.normal_update()
    for v in bm.verts: v.co += v.normal * offset
    bm.to_mesh(obj.data); bm.free()
    surface=('tunic' if material=='sage' else 'linen' if material=='cream' else
             'bracer' if 'wrist' in name else 'boot-cuff' if 'cuff' in name else
             'leggings' if 'leggings' in name else 'boot')
    obj.data.materials.clear(); obj.data.materials.append(surface_material(material,surface))
    if shell:
        mod = obj.modifiers.new('Constructed cloth thickness', 'SOLIDIFY'); mod.thickness = shell
    if material=='sage':cloth_folds(obj)
    uv_cylinder(obj)
    return obj

def band(low, high): return [((0,0,low),(0,0,-1)),((0,0,high),(0,0,1))]

shirt = clipped('Cream linen undershirt', band(1.65,3.10)+[((.87,0,0),(1,0,0)),((-.87,0,0),(-1,0,0))], 'cream', .030)
tunic = clipped('Sage fitted short tunic', band(1.73,2.98)+[((.60,0,0),(1,0,0)),((-.60,0,0),(-1,0,0))], 'sage', .068, .025)
pants = clipped('Fitted leather leggings', band(.72,1.79)+[((.66,0,0),(1,0,0)),((-.66,0,0),(-1,0,0))], 'leather', .026)
boots={}
for side in (-1,1):
    planes = band(.02,.82)+[((0,0,0),(-side,0,0))]
    boot=clipped('Boot '+str(side), planes, 'leather', .065, .04)
    boots[side]=boot
    clipped('Boot turned cuff '+str(side), band(.68,.86)+[((0,0,0),(-side,0,0))], 'leather', .100, .035)
    clipped('Leather wrist bracer '+str(side), band(1.97,2.31)+[((side*.66,0,0),(-side,0,0))], 'leather', .046, .022)

def weight(obj,bone):
    group=obj.vertex_groups.new(name=bone)
    group.add(list(range(len(obj.data.vertices))),1,'REPLACE')
    mod=obj.modifiers.new('Rig deformation','ARMATURE');mod.object=rig
    obj.parent=rig

def transfer_weights(obj):
    for group in body.vertex_groups:
        if group.name not in obj.vertex_groups:obj.vertex_groups.new(name=group.name)
    transfer=obj.modifiers.new('Fitted skin weights','DATA_TRANSFER')
    transfer.object=body;transfer.use_vert_data=True
    transfer.data_types_verts={'VGROUP_WEIGHTS'}
    transfer.vert_mapping='POLYINTERP_NEAREST'
    transfer.layers_vgroup_select_src='ALL';transfer.layers_vgroup_select_dst='NAME'
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.object.modifier_apply(modifier=transfer.name)
    if not any(m.type=='ARMATURE' for m in obj.modifiers):
        arm=obj.modifiers.new('Rig deformation','ARMATURE');arm.object=rig
    obj.parent=rig;obj.select_set(False)

def mesh(name, vertices, faces, material, bone=None, bevel=0):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);collection.objects.link(obj)
    surface=('skirt-front' if 'front skirt' in name else 'skirt-back' if 'back skirt' in name else
             'belt' if name=='Waist belt' else 'strap' if 'strap' in name else
             'hair-cap' if 'cap' in name else 'hair-lock' if material=='hair' else material)
    data.materials.append(surface_material(material,surface));uv_cylinder(obj)
    if 'skirt' in name:
        corners=[(0,1),(1,1),(1,0),(0,0)]
        for loop in data.loops:data.uv_layers.active.data[loop.index].uv=corners[loop.vertex_index]
    for poly in data.polygons:poly.use_smooth=True
    if bevel:
        mod=obj.modifiers.new('Worked edge','BEVEL');mod.width=bevel;mod.segments=2
    if bone:weight(obj,bone)
    return obj

def ellipsoid(name,location,scale,material,bone):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=16,location=location)
    obj=bpy.context.object;obj.name=name
    for old in list(obj.users_collection):old.objects.unlink(obj)
    collection.objects.link(obj)
    for v in obj.data.vertices:v.co = Vector(location)+Vector((v.co.x*scale[0],v.co.y*scale[1],v.co.z*scale[2]))
    obj.location=(0,0,0)
    obj.data.materials.append(materials[material]);uv_cylinder(obj)
    for poly in obj.data.polygons:poly.use_smooth=True
    weight(obj,bone);return obj

def ribbon(name,points,width,material,bone):
    if material=='hair':
        path=[]
        for i in range(len(points)-1):
            p0=Vector(points[max(0,i-1)]);p1=Vector(points[i]);p2=Vector(points[i+1]);p3=Vector(points[min(len(points)-1,i+2)])
            for j in range(8):
                t=j/8
                path.append(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t))
        path.append(Vector(points[-1]));vertices=[];faces=[];sides=8
        for i,p in enumerate(path):
            tangent=(path[min(i+1,len(path)-1)]-path[max(0,i-1)]).normalized()
            axis=Vector((tangent.z,0,-tangent.x)).normalized()
            taper=min(1,.18+i/4,.07+(len(path)-1-i)/5)
            for j in range(sides):
                angle=2*math.pi*j/sides
                vertices.append(p+axis*math.cos(angle)*width*.5*taper+Vector((0,math.sin(angle)*.018*taper,0)))
        for i in range(len(path)-1):
            for j in range(sides):faces.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
        obj=mesh(name,vertices,faces,material,bone)
        uv=obj.data.uv_layers.active
        for face in obj.data.polygons:
            for li in face.loop_indices:
                index=obj.data.loops[li].vertex_index
                uv.data[li].uv=((index%sides)/sides,(index//sides)/(len(path)-1))
        return obj
    vertices=[]
    for i,p in enumerate(points):
        tangent=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])
        side=Vector((tangent.z,0,-tangent.x)).normalized()*width/2
        vertices.extend([Vector(p)-side,Vector(p)+side])
    obj=mesh(name,vertices,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(len(points)-1)],material,bone)
    uv=obj.data.uv_layers.active
    for face in obj.data.polygons:
        for li in face.loop_indices:
            index=obj.data.loops[li].vertex_index
            uv.data[li].uv=(index%2,(index//2)/(len(points)-1))
    return obj

def curve(name,points,radius,material,bone):
    data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D';data.bevel_depth=radius;data.bevel_resolution=2
    spl=data.splines.new('BEZIER');spl.bezier_points.add(len(points)-1)
    for point,co in zip(spl.bezier_points,points):point.co=co;point.handle_left_type=point.handle_right_type='AUTO'
    obj=bpy.data.objects.new(name,data);collection.objects.link(obj)
    obj.data.materials.append(materials[material])
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active=obj;obj.select_set(True);bpy.ops.object.convert(target='MESH');obj.select_set(False)
    uv_cylinder(obj);weight(obj,bone)
    return obj

for side,bone in ((1,'foot.L'),(-1,'foot.R')):
    boot=boots[side]
    for modifier in list(boot.modifiers):boot.modifiers.remove(modifier)
    bm=bmesh.new();bm.from_mesh(boot.data)
    bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)
    for vertex in bm.verts:vertex.co.z=max(.035,vertex.co.z)
    bm.to_mesh(boot.data);bm.free()
    # The toe volume becomes part of one continuous boot, not a separate oval.
    toe=ellipsoid('Toe construction volume',(side*.497,-.26,.145),(.18,.24,.12),'leather',bone)
    bpy.ops.object.select_all(action='DESELECT');boot.select_set(True);toe.select_set(True)
    bpy.context.view_layer.objects.active=boot;bpy.ops.object.join()
    remesh=boot.modifiers.new('Continuous boot construction','REMESH')
    remesh.mode='VOXEL';remesh.voxel_size=.025;remesh.use_smooth_shade=True
    bpy.ops.object.modifier_apply(modifier=remesh.name)
    smooth=boot.modifiers.new('Sculpted toe and ankle','SMOOTH');smooth.factor=.7;smooth.iterations=3
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    for vertex in boot.data.vertices:vertex.co.z=max(.035,vertex.co.z)
    boot.vertex_groups.clear();transfer_weights(boot)
    boot.data.materials.clear();boot.data.materials.append(surface_material('leather','boot'))
    uv_cylinder(boot)
    for face in boot.data.polygons:face.use_smooth=True

# Pattern loops form clean collar and hem boundaries, independent of skin triangles.
def ring(name,z,rx,ry,height,material,bone):
    vertices=[];n=48
    for level in (z-height/2,z+height/2):
        for i in range(n):
            a=2*math.pi*i/n;vertices.append((rx*math.sin(a),-ry*math.cos(a),level))
    return mesh(name,vertices,[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],material,bone)

ring('Waist belt',1.86,.445,.405,.14,'leather','hips')
ring('Cream folded collar',3.00,.22,.19,.20,'cream','neck')
curve('Collar front fold',[(-.21,-.16,3.04),(0,-.25,2.89),(.18,-.17,3.04)],.045,'cream','neck')
curve('Collar second fold',[(-.17,-.18,3.00),(0,-.275,2.87),(.14,-.21,3.01)],.023,'cream','neck')
# Two split panels with clean constructed lower edges.
for side in (-1,1):
    vertices=[(side*.045,-.41,1.87),(side*.31,-.35,1.87),(side*.42,-.36,1.37),(side*.07,-.43,1.42)]
    panel=mesh('Split sage front skirt '+str(side),vertices,[(0,1,2,3)],'sage','hips',.008)
    solid=panel.modifiers.new('Hem thickness','SOLIDIFY');solid.thickness=.025
    curve('Cream tunic piping '+str(side),[vertices[1],vertices[2],vertices[3]],.04,'cream','hips')
    vertices=[(side*.03,.24,1.87),(side*.30,.20,1.87),(side*.38,.26,1.41),(side*.05,.30,1.43)]
    panel=mesh('Split sage back skirt '+str(side),vertices,[(3,2,1,0)],'sage','hips',.008)
    solid=panel.modifiers.new('Hem thickness','SOLIDIFY');solid.thickness=.025

def front_surface(obj,x,z,offset):
    bpy.context.view_layer.update()
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    data=evaluated.to_mesh();data.calc_loop_triangles()
    tree=BVHTree.FromPolygons([v.co.copy() for v in data.vertices],[tuple(t.vertices) for t in data.loop_triangles],all_triangles=True)
    hit,_,_,_=tree.ray_cast(Vector((x,-5,z)),Vector((0,1,0)))
    evaluated.to_mesh_clear()
    if hit is None:raise ValueError('Surface fitting missed '+obj.name)
    return hit.y-offset

chest_points=[(-.32,2.92),(-.22,2.75),(0,2.48),(.26,2.19),(.33,1.86)]
strap=ribbon('Diagonal chest strap',[(x,front_surface(tunic,x,z,.015),z) for x,z in chest_points],.13,'leather','chest')
back=ribbon('Diagonal back strap',[(-.32,.22,2.97),(-.20,.34,2.71),(.10,.31,2.32),(.32,.29,1.86)],.10,'leather','chest')
for obj in (strap,back):
    for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
    obj.vertex_groups.clear();transfer_weights(obj)

def buckle(name,center,width,height,bone):
    x,y,z=center
    points=[(x-width/2,y,z-height/2),(x+width/2,y,z-height/2),(x+width/2,y,z+height/2),(x-width/2,y,z+height/2),(x-width/2,y,z-height/2)]
    curve(name,points,.018,'brass',bone)
    curve(name+' tongue',[(x,y-.006,z-height/2),(x,y-.006,z+height*.15)],.011,'brass',bone)
buckle('Brass waist buckle',(0,-.421,1.86),.17,.12,'hips')
buckle('Brass chest fastening',(-.19,front_surface(tunic,-.19,2.74,.032),2.74),.11,.105,'chest')
ellipsoid('Travel satchel',(.45,-.015,1.65),(.20,.15,.24),'leather','hips')
ribbon('Satchel flap',[(.31,-.16,1.84),(.45,-.18,1.83),(.57,-.13,1.81)],.18,'leather','hips')
buckle('Satchel buckle',(.45,-.176,1.68),.075,.095,'hips')

# A connected skull-fitted cap with an asymmetric hairline; locks follow its mass.
vertices=[];faces=[];n=64;rows=16
for j in range(rows):
    for i in range(n):
        az=2*math.pi*i/n
        front=(1+math.cos(az))/2
        polar=(.02+j/(rows-1))*(2.25-.78*front)
        vertices.append((.35*math.sin(polar)*math.sin(az),-.16-.365*math.sin(polar)*math.cos(az),3.79+.315*math.cos(polar)))
for j in range(rows-1):
    for i in range(n):faces.append(((j+1)*n+i,(j+1)*n+(i+1)%n,j*n+(i+1)%n,j*n+i))
hair=mesh('Continuous sculpted auburn cap',vertices,faces,'hair','head')
for loop in hair.data.loops:
    index=loop.vertex_index
    hair.data.uv_layers.active.data[loop.index].uv=((index%n)/n,(index//n)/(rows-1))
ellipsoid('Auburn tied bun',(0,.24,3.70),(.17,.14,.16),'hair','head')
for i in range(2):
    x=-.09+i*.21
    ribbon('Swept fringe lock '+str(i),[(x,-.30,4.06),(x-.035,-.47,3.98),(x-.09,-.53,3.87),(x-.13,-.50,3.78+i*.035)],.22,'hair','head')
for side in (-1,1):
    ribbon('Temple lock '+str(side),[(side*.30,-.31,3.91),(side*.34,-.36,3.72),(side*.31,-.32,3.55)],.07,'hair','head')
    curve('Back tied lock '+str(side),[(side*.24,.08,3.99),(side*.27,.19,3.81),(side*.11,.31,3.71)],.023,'hair','head')

# Orbital inserts and lids stay inside the face silhouette, with deliberate brows.
for side in (-1,1):
    y=min(front_surface(body,side*.133+dx,3.655+dz,.008) for dx in (-.079,0,.079) for dz in (-.070,0,.070))
    ellipsoid('Eye ivory '+str(side),(side*.133,y,3.655),(.065,.008,.047),'cream','head')
    ellipsoid('Green iris '+str(side),(side*.137,y-.009,3.654),(.042,.003,.034),'eye','head')
    ellipsoid('Pupil '+str(side),(side*.137,y-.013,3.654),(.026,.002,.029),'ink','head')
    lids=[(side*.076,3.691),(side*.133,3.717),(side*.190,3.691)]
    curve('Upper eyelid '+str(side),[(x,min(y-.004,front_surface(body,x,z,.009)),z) for x,z in lids],.008,'facial-mark','head')
    brows=[(side*.075,3.737),(side*.140,3.755),(side*.200,3.740)]
    curve('Auburn brow '+str(side),[(x,front_surface(body,x,z,.008),z) for x,z in brows],.011,'facial-mark','head')
curve('Soft smile',[(x,front_surface(body,x,z,.006),z) for x,z in [(-.070,3.454),(0,3.443),(.070,3.454)]],.012,'hair','head')

# A modeled bridge and tip survive the two-pixel nose budget in the native view.
nose_points=[(-.036,3.635),(.036,3.635),(-.058,3.530),(.058,3.530),(0,3.504)]
nose_vertices=[(x,front_surface(body,x,z,.009),z) for x,z in nose_points]
nose_vertices.append((0,min(p[1] for p in nose_vertices)-.075,3.546))
nose=mesh('Modeled nose bridge',nose_vertices,[(0,1,5),(1,3,5),(3,4,5),(4,2,5),(2,0,5)],'skin')
transfer_weights(nose)
for obj in list(collection.objects):
    if obj.name.startswith(('Eye ivory','Green iris','Pupil','Upper eyelid','Auburn brow','Soft smile')):
        for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
        obj.vertex_groups.clear();transfer_weights(obj)
# Covered anatomy is hidden after deriving garments; toes must not protrude through boots.
bm=bmesh.new();bm.from_mesh(body.data)
bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.calc_center_median().z<3.02 and abs(f.calc_center_median().x)<.80],context='FACES')
bm.to_mesh(body.data);bm.free()

# Native 64px budget: compact legs while preserving head/hand detail and ground density.
def compact(p):
    p=p.copy();p.z=p.z*.78 if p.z<1.7 else p.z-.374
    p.x*=.92;p.y*=.78;p.z*=.74
    return p
for obj in collection.objects:
    if obj.type=='MESH':
        for vertex in obj.data.vertices:vertex.co=compact(vertex.co)
bpy.ops.object.select_all(action='DESELECT');bpy.context.view_layer.objects.active=rig;rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for bone in rig.data.edit_bones:bone.head=compact(bone.head);bone.tail=compact(bone.tail)
bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)

head_center=rig.data.bones['head'].head_local.copy()
for obj in collection.objects:
    if obj.type!='MESH' or 'head' not in obj.vertex_groups:continue
    index=obj.vertex_groups['head'].index
    for vertex in obj.data.vertices:
        amount=next((group.weight for group in vertex.groups if group.group==index),0)
        vertex.co.x=head_center.x+(vertex.co.x-head_center.x)*(1+.20*amount)
        vertex.co.y=head_center.y+(vertex.co.y-head_center.y)*(1+.08*amount)

for obj in collection.objects:
    if obj.type=='MESH':
        for mod in obj.modifiers:
            if mod.type=='SOLIDIFY':mod.thickness*=.74
            elif mod.type=='BEVEL':mod.width*=.74
            mod.show_render=mod.show_viewport
            if mod.type=='SUBSURF':mod.render_levels=mod.levels
scene.render.engine='BLENDER_EEVEE'
scene.world.color=(.15,.15,.15)
scene.view_settings.view_transform='Standard'
scene['Design']='Mira Fenway — sage ranger with cream linen, auburn swept hair, brown travel leather, brass fastenings'
scene['Native ground tile pixels']=64
scene['Pixels per world unit']=24
scene['Native visible target pixels']=64
rig['Foundation']='Blender Studio Human Base Meshes v1.4.1, CC0; installed Spriteforge anatomical base'
bpy.context.preferences.filepaths.save_version=0
ROOT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'mira-source.blend'),compress=True)
settings={'collection':'Mira','size':[128,128],'pixels_per_unit':24,'palette':{name:palette[name] for name in ('skin','sage','cream','hair','leather','brass','eye','ink')},'directions':['south','east','north','west'],'frames':[1],'fps':12,'pivot':[0,0,0],'anchor':[.70,.75],'shear':[0,.85],'light':[-.5,-.65,1],'outline':None,'shading':'preserve','tileable':False}
(ROOT/'prototype.json').write_text(json.dumps(settings,indent=2)+'\n')
print(json.dumps({'source':str(ROOT/'mira-source.blend'),'height':max(v.co.z for v in body.data.vertices),'objects':len(collection.objects)}))
