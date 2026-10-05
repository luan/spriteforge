"""Render source geometry and surface paint from four physical camera views."""
import argparse
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_scene import inspect, sha256, snapshots
from settings import DIRECTIONS, Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    settings = Settings.load(args.output/'asset.json')
    if bpy.app.version < (5,2,0):
        raise ValueError('Blender 5.2 or newer is required')
    digest = sha256(args.source)
    bpy.ops.wm.open_mainfile(filepath=str(args.source), use_scripts=False)
    source = bpy.context.scene
    inspect(args.source, args.output/'inspection.json')
    # Four evenly spaced motion samples expose both contacts and swing poses.
    frames = list(dict.fromkeys(settings.frames[i*len(settings.frames)//4] for i in range(4)))
    meshes = {}
    points = []
    for frame in frames:
        source.frame_set(frame)
        meshes[frame] = snapshots(source, settings.collection)
        points.extend(world @ vertex.co for mesh, world in meshes[frame] for vertex in mesh.vertices)
    bottom, top = min(p.z for p in points), max(p.z for p in points)
    height = top-bottom
    radius = max(((p.x-settings.pivot[0])**2+(p.y-settings.pivot[1])**2)**.5 for p in points)
    scale = max(height*1.2, radius*2.5)
    center = Vector((settings.pivot[0], settings.pivot[1], (top+bottom)/2))
    scene = bpy.data.scenes.new('Model review')
    scene.render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x = scene.render.resolution_y = 384
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.world = bpy.data.worlds.new('Review studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.08,.09,.11,1)
    camera = bpy.data.objects.new('Review camera', bpy.data.cameras.new('Review camera'))
    scene.collection.objects.link(camera)
    camera.data.type = 'ORTHO'; camera.data.ortho_scale = scale
    camera.location = center+Vector((0,-scale*3,scale))
    camera.rotation_euler = (center-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.camera = camera
    for name, position, energy, size in [('Key',(-3,-4,6),650,4),('Fill',(4,-2,3),350,5),('Rim',(0,3,5),500,3)]:
        light = bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'))
        light.location = Vector(position)*height/3
        light.rotation_euler = (center-light.location).to_track_quat('-Z','Y').to_euler()
        light.data.energy = energy*(height/3)**2
        light.data.shape = 'DISK'; light.data.size = size*height/3
        scene.collection.objects.link(light)
    clay = bpy.data.materials.new('Neutral construction review')
    clay.use_nodes = True
    shader = clay.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (.44,.47,.52,1)
    shader.inputs['Roughness'].default_value = 1
    shader.inputs['Specular IOR Level'].default_value = 0
    for stage in ('clay','paint'):
        (args.output/stage).mkdir()
        for frame in frames:
            for direction, angle in DIRECTIONS.items():
                pivot = Vector(settings.pivot)
                transform = Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(angle),4,'Z') @ Matrix.Translation(-pivot)
                proxies = []
                for mesh, world in meshes[frame]:
                    copy = mesh.copy(); copy.transform(transform@world)
                    if stage == 'clay':
                        copy.materials.clear(); copy.materials.append(clay)
                        for polygon in copy.polygons: polygon.material_index = 0
                    obj = bpy.data.objects.new('Review surface',copy)
                    scene.collection.objects.link(obj); proxies.append(obj)
                bpy.context.window.scene = scene
                scene.frame_set(frame)
                scene.render.filepath = str(args.output/stage/f'{direction}-{frame:04d}.png')
                bpy.ops.render.render(write_still=True,scene=scene.name)
                for obj in proxies:
                    mesh=obj.data; bpy.data.objects.remove(obj,do_unlink=True); bpy.data.meshes.remove(mesh)
    for samples in meshes.values():
        for mesh,_ in samples: bpy.data.meshes.remove(mesh)
    if sha256(args.source)!=digest: raise ValueError('review changed its input')
    (args.output/'manifest.json').write_text(json.dumps({'source':str(args.source),'source_sha256':digest,
        'source_unchanged':True,'frames':frames,'directions':list(DIRECTIONS),'cell_size':384,
        'projection':'physical orthographic studio camera; original evaluated meshes; no sprite shear'},indent=2)+'\n')


if __name__ == '__main__':
    main()
