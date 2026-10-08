"""Small authored-alpha and full-ground assets for the public preparation CLI."""
import argparse
import sys
from pathlib import Path

import bpy

parser = argparse.ArgumentParser()
parser.add_argument('--skill', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--opaque', action='store_true')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
sys.path.insert(0, str(args.skill/'scripts'))
from materials import lit_material, pixel_material

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
collection = bpy.data.collections.new('Fixture')
bpy.context.scene.collection.children.link(collection)
image = bpy.data.images.new('Authored alpha', width=16, height=16, alpha=True)
image.pixels = [value for y in range(16) for x in range(16)
                for value in (.8, .15, .55, 1 if (x//4+y//4) % 2 else 0)]
texture = args.output.parent/'cutout.png'
image.filepath_raw, image.file_format = str(texture), 'PNG'
image.save()
for index, kind in enumerate(['painted', 'lit']):
    material = (pixel_material(kind, texture=texture) if kind == 'painted'
                else lit_material(kind, 'ffffff', texture, paint_strength=.4))
    bpy.ops.mesh.primitive_plane_add(size=1.2, location=(-.8+1.6*index, 0, 0))
    plane = bpy.context.object
    plane.data.materials.append(material)
    for old in list(plane.users_collection):
        old.objects.unlink(plane)
    collection.objects.link(plane)
    if index == 0:
        shared = plane.copy()
        shared.location.y = 1.5
        collection.objects.link(shared)
if args.opaque:
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, -.05))
    ground = bpy.context.object
    ground.data.materials.append(lit_material('Ground', '394e72'))
    for old in list(ground.users_collection):
        old.objects.unlink(ground)
    collection.objects.link(ground)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(args.output), compress=True)
