#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow>=12.1,<13"]
# ///
"""Prepare a real rig's clay sheet or inspect a whole-sheet paint edit."""
import argparse
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys


def clay(source: Path, output: Path, collection: str | None) -> None:
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
    objects = bpy.data.collections[collection].all_objects if collection else bpy.context.scene.objects
    material = bpy.data.materials.new('Sheet clay')
    material.use_nodes = True
    surface = material.node_tree.nodes.get('Principled BSDF')
    surface.inputs['Base Color'].default_value = (.55, .55, .55, 1)
    surface.inputs['Roughness'].default_value = .8
    surface.inputs['Specular IOR Level'].default_value = .15
    for obj in objects:
        if obj.type in ('MESH', 'CURVE', 'SURFACE', 'FONT', 'META'):
            if not obj.material_slots:
                obj.data.materials.append(material)
            for slot in obj.material_slots:
                slot.material = material
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)


def prepare(args: argparse.Namespace) -> None:
    from PIL import Image
    from settings import Settings
    source = args.source.resolve()
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    original = Settings.load(args.config)
    frames = original.frames[::args.step]
    interval = frames[1] - frames[0] if len(frames) > 1 else args.step
    if any(b-a != interval for a, b in zip(frames, frames[1:])):
        raise ValueError('sheet frames must be evenly spaced for held-pose playback')
    settings = replace(original, frames=frames, supersample=4,
                       outline=None, object_outline=None, opaque=False)
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    settings.save(root/'clay.json')
    command = [args.blender, '--background', '--factory-startup', '--disable-autoexec',
               '--python-exit-code', '1', '--python', str(Path(__file__).resolve()),
               '--', '--clay-stage', '--source', str(source), '--output', str(root/'clay.blend')]
    if settings.collection:
        command.extend(['--collection', settings.collection])
    with (root/'clay.log').open('w') as log:
        subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
    with (root/'render.log').open('w') as log:
        subprocess.run(['uv', 'run', '--script', str(Path(__file__).with_name('pipeline.py')),
                        'render', '--source', str(root/'clay.blend'), '--config', str(root/'clay.json'),
                        '--output', str(root/'render'), '--blender', args.blender],
                       check=True, stdout=log, stderr=subprocess.STDOUT)
    if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
        raise ValueError('original model changed during clay preparation')
    surface_render = None
    if args.surface_guide:
        surface_render = root/'surface-render'
        with (root/'surface.log').open('w') as log:
            subprocess.run(['uv', 'run', '--script', str(Path(__file__).with_name('pipeline.py')),
                            'render', '--source', str(source), '--config', str(root/'clay.json'),
                            '--output', str(surface_render), '--blender', args.blender],
                           check=True, stdout=log, stderr=subprocess.STDOUT)
        if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise ValueError('original model changed during surface preparation')
    print(json.dumps(pack_sheet(root, settings.directions, frames, settings.fps/interval,
                               source, digest, surface_render)))


def cell_origin(direction: int, phase: int, phases: int, columns: int, cell: tuple[int, int]) -> tuple[int, int]:
    index = direction*phases+phase
    return (index % columns)*cell[0], (index // columns)*cell[1]


def pack_sheet(root: Path, directions: tuple[str, ...], frames: tuple[int, ...], fps: float,
               source: Path, digest: str, surface_render: Path | None = None) -> dict:
    from PIL import Image
    boxes = []
    for direction in directions:
        for frame in frames:
            with Image.open(root/'render/raw'/f'{direction}-{frame:04d}.png') as im:
                boxes.append(im.getchannel('A').point(lambda a: 255 if a >= 128 else 0).getbbox())
    if any(box is None for box in boxes):
        raise ValueError('empty clay cell; inspect the source collection and camera')
    left = math.floor(min(b[0] for b in boxes)/4)-4
    top = math.floor(min(b[1] for b in boxes)/4)-4
    width = math.ceil((math.ceil(max(b[2] for b in boxes)/4)+4-left)/8)*8
    height = math.ceil((math.ceil(max(b[3] for b in boxes)/4)+4-top)/8)*8
    crop = (left, top, left+width, top+height)
    count = len(frames)*len(directions)
    columns = min(count, 8, max(1, 2**round(math.log2(math.sqrt(count*height/width)))))
    rows = math.ceil(count/columns)
    size = (width*columns, height*rows)
    sheet = Image.new('RGBA', tuple(v*4 for v in size))
    surface_sheet = Image.new('RGBA', sheet.size) if surface_render else None
    native = Image.new('RGBA', size)
    for row, direction in enumerate(directions):
        for column, frame in enumerate(frames):
            x, y = cell_origin(row, column, len(frames), columns, (width, height))
            name = f'{direction}-{frame:04d}.png'
            with Image.open(root/'render/raw'/name) as im:
                raw_size = im.size
                sheet.paste(im.crop(tuple(v*4 for v in crop)), (x*4, y*4))
            with Image.open(root/'render/sprites'/name) as im:
                native.paste(im.crop(crop), (x, y))
            if surface_sheet is not None:
                with Image.open(surface_render/'raw'/name) as im:
                    if im.size != raw_size:
                        raise ValueError('surface guide must use the same render size as clay')
                    surface_sheet.paste(im.crop(tuple(v*4 for v in crop)), (x*4, y*4))
    sheet.save(root/'clay-sheet.png')
    native.save(root/'clay-native.png')
    native.getchannel('A').save(root/'geometry-mask.png')
    metadata = {'directions': list(directions), 'source_frames': list(frames),
                'crop': list(crop), 'cell': [width, height], 'paint_scale': 4,
                'columns': columns, 'rows': rows,
                'input_size': list(sheet.size), 'output_native_size': list(size),
                'preview_fps': fps, 'source': str(source), 'source_sha256': digest}
    if surface_sheet is not None:
        surface_sheet.save(root/'surface-sheet.png')
        metadata['surface_guide'] = 'surface-sheet.png'
    (root/'sheet.json').write_text(json.dumps(metadata, indent=2)+'\n')
    return metadata


def finish(args: argparse.Namespace) -> None:
    from PIL import Image, ImageChops
    metadata = json.loads((args.prepared/'sheet.json').read_text())
    width, height = metadata['cell']
    size = tuple(metadata['output_native_size'])
    phases = len(metadata['source_frames'])
    columns = metadata.get('columns', phases)
    with Image.open(args.painted) as raw:
        if abs(raw.width/raw.height/(size[0]/size[1])-1) > .01:
            raise ValueError('paint canvas aspect ratio changed; repair the sheet layout before exporting')
        paint = raw.convert('RGBA').resize(size, Image.Resampling.BOX)
    paint.putalpha(paint.getchannel('A').point(lambda a: 255 if a >= 128 else 0))
    mask = Image.open(args.prepared/'geometry-mask.png').convert('L')
    if mask.size != size:
        raise ValueError('geometry mask does not match sheet metadata')
    raw_paint = paint.copy()
    if args.clip_to_geometry:
        # Remove overshoot; never invent coverage where the paint missed geometry.
        paint.putalpha(ImageChops.multiply(paint.getchannel('A'), mask))
        paint = Image.composite(paint, Image.new('RGBA', size), paint.getchannel('A'))
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    (root/'sprites').mkdir()
    report = []
    overlay = raw_paint.copy()
    for row, direction in enumerate(metadata['directions']):
        for column, frame in enumerate(metadata['source_frames']):
            x, y = cell_origin(row, column, phases, columns, (width, height))
            box = (x, y, x+width, y+height)
            tile = paint.crop(box)
            raw_tile = raw_paint.crop(box)
            actual = raw_tile.getchannel('A')
            target = mask.crop(box)
            union = ImageChops.lighter(actual, target).histogram()[255]
            intersection = ImageChops.multiply(actual, target).histogram()[255]
            extra = ImageChops.subtract(actual, target)
            missing = ImageChops.subtract(target, actual)
            if not actual.getbbox() or not target.getbbox():
                raise ValueError(f'empty cell: {direction}/{frame}')
            report.append({'direction': direction, 'source_frame': frame,
                           'silhouette_iou': intersection/union,
                           'outside_pixels': extra.histogram()[255],
                           'missing_pixels': missing.histogram()[255],
                           'exported_outside_pixels': ImageChops.subtract(tile.getchannel('A'), target).histogram()[255]})
            tile.save(root/'sprites'/f'{direction}-{frame:04d}.png')
            raw_tile.paste((255, 55, 55, 255), (0, 0, width, height), extra)
            raw_tile.paste((0, 220, 255, 255), (0, 0, width, height), missing)
            overlay.paste(raw_tile, (x, y))
    paint.save(root/'painted-native.png')
    overlay.save(root/'silhouette-drift.png')
    animation = []
    for column in range(len(metadata['source_frames'])):
        preview = Image.new('RGBA', (width*len(metadata['directions']), height))
        for row in range(len(metadata['directions'])):
            x, y = cell_origin(row, column, phases, columns, (width, height))
            preview.paste(paint.crop((x, y, x+width, y+height)), (row*width, 0))
        animation.append(preview)
    animation[0].save(root/'preview.webp', save_all=True, append_images=animation[1:],
                      duration=round(1000/metadata['preview_fps']), loop=0, lossless=True, exact=True)
    (root/'boundary-report.json').write_text(json.dumps(report, indent=2)+'\n')
    metadata.update(painted=str(args.painted.resolve()), visual_acceptance='unreviewed',
                    clip_to_geometry=args.clip_to_geometry,
                    boundary_report_measures='raw paint before geometry clipping')
    (root/'sheet.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps({'output': str(root), 'silhouette_iou_range':
                     [min(r['silhouette_iou'] for r in report), max(r['silhouette_iou'] for r in report)]}))


def main() -> None:
    if '--clay-stage' in sys.argv:
        parser = argparse.ArgumentParser()
        parser.add_argument('--clay-stage', action='store_true')
        parser.add_argument('--source', type=Path, required=True)
        parser.add_argument('--output', type=Path, required=True)
        parser.add_argument('--collection')
        args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
        clay(args.source, args.output, args.collection)
        return
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prepare_parser = sub.add_parser('prepare')
    prepare_parser.add_argument('--source', type=Path, required=True)
    prepare_parser.add_argument('--config', type=Path, required=True)
    prepare_parser.add_argument('--step', type=int, default=1)
    prepare_parser.add_argument('--blender', default='blender')
    prepare_parser.add_argument('--surface-guide', action='store_true',
                                help='also render the original materials in the same sheet layout')
    prepare_parser.add_argument('--output', type=Path, required=True)
    finish_parser = sub.add_parser('finish')
    finish_parser.add_argument('--prepared', type=Path, required=True)
    finish_parser.add_argument('--painted', type=Path, required=True)
    finish_parser.add_argument('--output', type=Path, required=True)
    finish_parser.add_argument('--clip-to-geometry', action='store_true',
                               help='remove paint outside the real model mask; retain missing coverage and raw drift evidence')
    args = parser.parse_args()
    if args.command == 'prepare':
        if args.step < 1:
            parser.error('--step must be positive')
        prepare(args)
    else:
        finish(args)


if __name__ == '__main__':
    main()
