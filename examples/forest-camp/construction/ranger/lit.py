"""Replace unlit study paint with textured materials, retaining the actual rig and UVs."""
import argparse
from pathlib import Path
import sys
import bpy

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--skill', type=Path, required=True)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--textures', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
if args.output.exists():
    raise ValueError('Output must be fresh')
sys.path.insert(0, str(args.skill / 'scripts'))
from materials import lit_material

bpy.ops.wm.open_mainfile(filepath=str(args.source), use_scripts=False)
colors = {'skin':'e2ab82', 'sage':'637c4e', 'cream':'d7c49d',
          'hair':'a95b2d', 'leather':'8c6039', 'brass':'d5aa58',
          'eye':'3f6651', 'ink':'181c1b', 'facial-mark':'583a29',
          'eye-white':'d9d0b8'}
cache = {}
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH':
        continue
    for slot in obj.material_slots:
        original = slot.material
        if original is None:
            continue
        role = original.name.split('.')[0]
        if obj.name.startswith('Eye ivory'):
            role = 'eye-white'
        if role not in colors:
            raise ValueError('Unspecified material: ' + role)
        image = next((n.image for n in original.node_tree.nodes
                      if n.type == 'TEX_IMAGE' and n.image), None)
        path = args.textures / (Path(image.filepath).stem + '.png') if image else None
        # Skin/metal guides contain baked lighting; do not illuminate them twice.
        if role in ('skin', 'brass', 'eye-white') or path is not None and not path.exists():
            path = None
        key = (role, path)
        if key not in cache:
            cache[key] = lit_material(role, colors[role], path,
                roughness=.4 if role == 'brass' else .65 if role == 'leather' else .85,
                metallic=.65 if role == 'brass' else 0)
        for node in cache[key].node_tree.nodes:
            if node.type=='TEX_IMAGE':node.interpolation='Linear'
        slot.material = cache[key]
scene = bpy.context.scene
scene['Surface treatment'] = 'Packed UV material fields; continuous diffuse shading; restrained material-specific gloss'
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(args.output), compress=True)
