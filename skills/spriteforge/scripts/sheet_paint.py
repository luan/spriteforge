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


def clay_material(original):
    """Neutralize color while keeping the author's UV cutouts and opacity."""
    import bpy
    material = original.copy() if original else bpy.data.materials.new('Sheet clay')
    material.name = 'Sheet clay / '+(original.name if original else 'default')
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    alpha = None
    for node in nodes:
        if node.type == 'BSDF_PRINCIPLED':
            alpha = node.inputs['Alpha']
            break
    if alpha is None:
        for node in nodes:
            if (node.type == 'MIX_SHADER' and node.inputs[1].is_linked
                    and node.inputs[1].links[0].from_node.type == 'BSDF_TRANSPARENT'):
                alpha = node.inputs[0]
                break
    surface = nodes.new('ShaderNodeBsdfPrincipled')
    surface.inputs['Base Color'].default_value = (.55, .55, .55, 1)
    surface.inputs['Roughness'].default_value = .8
    surface.inputs['Specular IOR Level'].default_value = .15
    if alpha is not None:
        if alpha.is_linked:
            links.new(alpha.links[0].from_socket, surface.inputs['Alpha'])
        else:
            surface.inputs['Alpha'].default_value = alpha.default_value
    output = next((node for node in nodes if node.type == 'OUTPUT_MATERIAL' and node.is_active_output), None)
    if output is None:
        output = nodes.new('ShaderNodeOutputMaterial')
    links.new(surface.outputs['BSDF'], output.inputs['Surface'])
    return material


def clay(source: Path, output: Path, collection: str | None) -> None:
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
    objects = bpy.data.collections[collection].all_objects if collection else bpy.context.scene.objects
    materials = {}

    def neutral(original):
        if original not in materials:
            material = clay_material(original)
            materials[original] = material
            # Shared mesh instances may already reference the replacement.
            materials[material] = material
        return materials[original]

    for obj in objects:
        if obj.type in ('MESH', 'CURVE', 'SURFACE', 'FONT', 'META'):
            if not obj.material_slots:
                obj.data.materials.append(neutral(None))
            for slot in obj.material_slots:
                slot.material = neutral(slot.material)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)


def sampled_clip(frames: tuple[int, ...], fps: float, step: int) -> tuple[tuple[int, ...], float]:
    """Source frame numbers locate poses; fps describes exported pose playback."""
    selected = frames[::step]
    interval = selected[1] - selected[0] if len(selected) > 1 else step
    if any(b-a != interval for a, b in zip(selected, selected[1:])):
        raise ValueError('sheet frames must be evenly spaced for held-pose playback')
    return selected, fps * len(selected) / len(frames)


def prepare(args: argparse.Namespace) -> None:
    from PIL import Image
    from settings import Settings
    source = args.source.resolve()
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    original = Settings.load(args.config)
    frames, fps = sampled_clip(original.frames, original.fps, args.step)
    settings = replace(original, frames=frames, supersample=4,
                       outline=None, object_outline=None)
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
    print(json.dumps(pack_sheet(root, settings.directions, frames, fps,
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
    render = json.loads((root/'render/manifest.json').read_text())
    if all(box == (0, 0, render['size'][0]*4, render['size'][1]*4) for box in boxes):
        # Full-cell ground has no transparent padding between neighboring tiles.
        left, top = 0, 0
        width, height = render['size']
    else:
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
    pose_identity = {}
    for row, direction in enumerate(directions):
        known_poses = {}
        canonical_frames = []
        for column, frame in enumerate(frames):
            x, y = cell_origin(row, column, len(frames), columns, (width, height))
            name = f'{direction}-{frame:04d}.png'
            with Image.open(root/'render/raw'/name) as im:
                raw_size = im.size
                sheet.paste(im.crop(tuple(v*4 for v in crop)), (x*4, y*4))
                clay_pixels = im.tobytes()
            with Image.open(root/'render/sprites'/name) as im:
                native.paste(im.crop(crop), (x, y))
            if surface_sheet is not None:
                with Image.open(surface_render/'raw'/name) as im:
                    if im.size != raw_size:
                        raise ValueError('surface guide must use the same render size as clay')
                    surface_sheet.paste(im.crop(tuple(v*4 for v in crop)), (x*4, y*4))
                    # Both geometry and authored surface appearance must match.
                    digest = hashlib.sha256(clay_pixels+im.tobytes()).hexdigest()
                    canonical_frames.append(known_poses.setdefault(digest, frame))
        if surface_sheet is not None:
            pose_identity[direction] = canonical_frames
    sheet.save(root/'clay-sheet.png')
    native.save(root/'clay-native.png')
    native.getchannel('A').save(root/'geometry-mask.png')
    metadata = {'directions': list(directions), 'source_frames': list(frames),
                'crop': list(crop), 'cell': [width, height], 'paint_scale': 4,
                'columns': columns, 'rows': rows,
                'input_size': list(sheet.size), 'output_native_size': list(size),
                'preview_fps': fps, 'source': str(source), 'source_sha256': digest}
    metadata.update(pixels_per_unit=render['pixels_per_unit'],
                    anchor=[(a*s-offset)/extent for a, s, offset, extent in
                            zip(render['anchor'], render['size'], crop[:2], (width, height))],
                    pivot=render['pivot'], shear=render['shear'])
    if surface_sheet is not None:
        surface_sheet.save(root/'surface-sheet.png')
        metadata['surface_guide'] = 'surface-sheet.png'
        metadata['pose_identity'] = pose_identity
    (root/'sheet.json').write_text(json.dumps(metadata, indent=2)+'\n')
    return metadata


def export_static_variants(root: Path, atlas, manifest: dict) -> None:
    """Export material states as independent, non-cycling runtime assets."""
    from PIL import Image
    width,height=manifest['size']
    assets={}
    for column,frame in enumerate(manifest['frames']):
        name=f'variant-{frame:04d}'
        directory=root/'variants'/name
        directory.mkdir(parents=True)
        tile_atlas=Image.new('RGBA',(width,height*len(manifest['directions'])))
        for row in range(len(manifest['directions'])):
            tile_atlas.paste(atlas.crop((column*width,row*height,
                                        (column+1)*width,(row+1)*height)),(0,row*height))
        tile_atlas.save(directory/'atlas.png')
        variant={key:manifest[key] for key in ('directions','anchor','pixels_per_unit','size','fps',
                    'source','source_sha256','pivot','shear','visual_acceptance') if key in manifest}
        variant.update(frames=[frame],atlas='atlas.png')
        if 'sheet' in manifest:
            variant['sheet']='../../'+manifest['sheet']
        (directory/'manifest.json').write_text(json.dumps(variant,indent=2)+'\n')
        assets[name]=str(directory.relative_to(root))
    (root/'variants.json').write_text(json.dumps({'assets':assets},indent=2)+'\n')


def hold_identical_poses(paint, mask, metadata):
    """Share paint only for poses with identical source geometry and UV renders."""
    from PIL import ImageChops
    frames = metadata['source_frames']
    phases = len(frames)
    cell = tuple(metadata['cell'])
    columns = metadata.get('columns', phases)
    holds = {}
    for row, direction in enumerate(metadata['directions']):
        identities = metadata.get('pose_identity', {}).get(direction, frames)
        if len(identities) != phases:
            raise ValueError('pose identity count does not match sheet frames')
        for column, canonical in enumerate(identities):
            if canonical == frames[column]:
                continue
            source = cell_origin(row, frames.index(canonical), phases, columns, cell)
            destination = cell_origin(row, column, phases, columns, cell)
            box = (*source, source[0]+cell[0], source[1]+cell[1])
            target_box = (*destination, destination[0]+cell[0], destination[1]+cell[1])
            if ImageChops.difference(mask.crop(box), mask.crop(target_box)).getbbox():
                raise ValueError('identical pose record has different geometry masks')
            paint.paste(paint.crop(box), destination)
            holds[f'{direction}-{frames[column]:04d}'] = canonical
    return holds


def register_canvas(paint, target):
    """Correct small whole-canvas drift without fitting individual poses."""
    from PIL import Image, ImageChops
    width, height = paint.size
    alpha = paint.getchannel('A')

    def transform(values):
        sx, sy, tx, ty = values
        return (1/sx, 0, width/2*(1-1/sx)-tx/sx,
                0, 1/sy, height/2*(1-1/sy)-ty/sy)

    def score(values):
        coverage = alpha.transform(paint.size, Image.Transform.AFFINE,
                                   transform(values), Image.Resampling.NEAREST)
        intersection = ImageChops.multiply(coverage, target).histogram()[255]
        union = ImageChops.lighter(coverage, target).histogram()[255]
        return intersection/union

    values = [1, 1, 0, 0]
    best = original = score(values)
    # Deliberately limited to 5% canvas drift. Larger changes need a new paint pass.
    for scale_step, shift_step in ((0, 4), (0, 2), (0, 1),
                                   (.04, 4), (.02, 2), (.01, 1), (.005, .5), (.002, .25)):
        if best == 1:
            break
        for _ in range(30):
            candidates = []
            for dimension, step in enumerate((scale_step, scale_step, shift_step, shift_step)):
                if not step:
                    continue
                for sign in (-1, 1):
                    candidate = values.copy()
                    candidate[dimension] += step*sign
                    if not (.95 <= candidate[0] <= 1.05 and .95 <= candidate[1] <= 1.05
                            and abs(candidate[2]) <= width*.05 and abs(candidate[3]) <= height*.05):
                        continue
                    candidates.append((score(candidate), candidate))
            if not candidates:
                break
            result, candidate = max(candidates, key=lambda pair: pair[0])
            if result <= best:
                break
            best, values = result, candidate
    registered = paint.transform(paint.size, Image.Transform.AFFINE,
                                  transform(values), Image.Resampling.NEAREST)
    return registered, {'scale': values[:2], 'translation_native_pixels': values[2:],
                        'raw_silhouette_iou': original, 'registered_silhouette_iou': best,
                        'scope': 'one whole-canvas transform; no per-pose fitting'}


def finish(args: argparse.Namespace) -> None:
    from PIL import Image, ImageChops
    from pixels import finish_image
    from settings import Settings
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
    if args.config:
        from settings import Settings
        config = Settings.load(args.config)
        metadata.update(pixels_per_unit=config.pixels_per_unit,
                        anchor=[(a*s-offset)/extent for a, s, offset, extent in
                                zip(config.anchor, config.size, metadata['crop'][:2], (width, height))],
                        pivot=config.pivot, shear=config.shear)
    if 'anchor' not in metadata or 'pixels_per_unit' not in metadata:
        raise ValueError('sheet lacks placement metadata; rerun prepare or supply --config with the original render profile')
    raw_paint = paint.copy()
    registration = None
    if args.register:
        paint, registration = register_canvas(paint, mask)
    holds = hold_identical_poses(paint, mask, metadata)
    registered_paint = paint.copy()
    if args.clip_to_geometry:
        # Remove overshoot; never invent coverage where the paint missed geometry.
        paint.putalpha(ImageChops.multiply(paint.getchannel('A'), mask))
        paint = Image.composite(paint, Image.new('RGBA', size), paint.getchannel('A'))
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    (root/'sprites').mkdir()
    if holds:
        (root/'identical-pose-holds.json').write_text(json.dumps(holds, indent=2)+'\n')
    if registration:
        (root/'registration.json').write_text(json.dumps(registration, indent=2)+'\n')
        registered_paint.save(root/'painted-registered.png')
    report = []
    overlay = raw_paint.copy()
    # Runtime atlases use one row per facing, independent of the paint grid.
    atlas = Image.new('RGBA', (width*phases, height*len(metadata['directions'])))
    for row, direction in enumerate(metadata['directions']):
        for column, frame in enumerate(metadata['source_frames']):
            x, y = cell_origin(row, column, phases, columns, (width, height))
            box = (x, y, x+width, y+height)
            tile = paint.crop(box)
            raw_tile = raw_paint.crop(box)
            actual = raw_tile.getchannel('A')
            target = mask.crop(box)
            registered = registered_paint.crop(box).getchannel('A')
            registered_union = ImageChops.lighter(registered, target).histogram()[255]
            clipped_alpha = tile.getchannel('A')
            if args.outline:
                tile = finish_image(tile, Settings(size=(width, height),
                    pixels_per_unit=metadata['pixels_per_unit'], outline=args.outline))
                paint.paste(tile, (x, y))
            union = ImageChops.lighter(actual, target).histogram()[255]
            intersection = ImageChops.multiply(actual, target).histogram()[255]
            extra = ImageChops.subtract(actual, target)
            missing = ImageChops.subtract(target, actual)
            if not actual.getbbox() or not target.getbbox():
                raise ValueError(f'empty cell: {direction}/{frame}')
            report.append({'direction': direction, 'source_frame': frame,
                           'held_from_source_frame': holds.get(f'{direction}-{frame:04d}', frame),
                           'silhouette_iou': intersection/union,
                           'outside_pixels': extra.histogram()[255],
                           'missing_pixels': missing.histogram()[255],
                           'registered_silhouette_iou': ImageChops.multiply(registered, target).histogram()[255]/registered_union,
                           'registered_missing_pixels': ImageChops.subtract(target, registered).histogram()[255],
                           'registered_outside_pixels': ImageChops.subtract(registered, target).histogram()[255],
                           'paint_outside_pixels': ImageChops.subtract(clipped_alpha, target).histogram()[255],
                           'outline_pixels': ImageChops.subtract(tile.getchannel('A'), clipped_alpha).histogram()[255],
                           'exported_outside_pixels': ImageChops.subtract(tile.getchannel('A'), target).histogram()[255]})
            tile.save(root/'sprites'/f'{direction}-{frame:04d}.png')
            atlas.paste(tile, (column*width, row*height))
            raw_tile.paste((255, 55, 55, 255), (0, 0, width, height), extra)
            raw_tile.paste((0, 220, 255, 255), (0, 0, width, height), missing)
            overlay.paste(raw_tile, (x, y))
    paint.save(root/'painted-native.png')
    atlas.save(root/'atlas.png')
    manifest = {key: metadata[key] for key in ('directions', 'anchor', 'pixels_per_unit')}
    manifest.update(size=[width, height], frames=metadata['source_frames'],
                    fps=metadata['preview_fps'], atlas='atlas.png',
                    sheet='sheet.json', outline=args.outline, visual_acceptance='unreviewed')
    for key in ('source', 'source_sha256', 'pivot', 'shear'):
        if key in metadata:
            manifest[key] = metadata[key]
    if args.variants:
        export_static_variants(root,atlas,manifest)
    else:
        (root/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    overlay.save(root/'silhouette-drift.png')
    animation = []
    for column in range(len(metadata['source_frames'])):
        preview = Image.new('RGBA', (width*len(metadata['directions']), height))
        for row in range(len(metadata['directions'])):
            x, y = cell_origin(row, column, phases, columns, (width, height))
            preview.paste(paint.crop((x, y, x+width, y+height)), (row*width, 0))
        animation.append(preview)
    if not args.variants:
        animation[0].save(root/'preview.webp', save_all=True, append_images=animation[1:],
                          duration=round(1000/metadata['preview_fps']), loop=0, lossless=True, exact=True)
    (root/'boundary-report.json').write_text(json.dumps(report, indent=2)+'\n')
    metadata.update(painted=str(args.painted.resolve()), visual_acceptance='unreviewed',
                    clip_to_geometry=args.clip_to_geometry, outline=args.outline,
                    register_canvas=args.register,
                    frame_mode='static_variants' if args.variants else 'animation',
                    boundary_report_measures='raw paint before registration and geometry clipping')
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
    finish_parser.add_argument('--config', type=Path,
                               help='original render profile for older sheets without placement metadata')
    finish_parser.add_argument('--variants', action='store_true',
                               help='export each source state as an independent static asset instead of an animation')
    finish_parser.add_argument('--clip-to-geometry', action='store_true',
                               help='remove paint outside the real model mask; retain missing coverage and raw drift evidence')
    finish_parser.add_argument('--register', action='store_true',
                               help='correct small whole-canvas drift; retain pose placement, model masks and raw measurements')
    from settings import hexcolor
    finish_parser.add_argument('--outline', type=hexcolor,
                               help='add a one-pixel exterior contour after clipping; preserve interior paint and holes')
    args = parser.parse_args()
    if args.command == 'prepare':
        if args.step < 1:
            parser.error('--step must be positive')
        prepare(args)
    else:
        finish(args)


if __name__ == '__main__':
    main()
