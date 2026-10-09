#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow>=12.1,<13"]
# ///
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image


SCRIPT = Path(__file__).resolve().parents[1] / 'skills/spriteforge/scripts/sheet_paint.py'


class SheetPaintTests(unittest.TestCase):
    def test_finish_preserves_cells_and_animation_in_both_layouts(self):
        for columns in (3, 2):
            with self.subTest(columns=columns), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                cell = (8, 8)
                directions = ['south', 'west']
                frames = [1, 3, 5]
                size = (cell[0]*columns, cell[1]*(6//columns))
                sheet = Image.new('RGBA', size)
                tiles = []
                for index in range(6):
                    tile = Image.new('RGBA', cell)
                    tile.paste((30+index*30, 83, 147, 255), (1, 2, 7, 7))
                    tile.putpixel((2, 3), (255, index*20, 0, 255))
                    tiles.append(tile)
                    sheet.paste(tile, ((index % columns)*8, (index//columns)*8))
                sheet.save(root/'paint.png')
                sheet.getchannel('A').save(root/'geometry-mask.png')
                metadata = {'cell': cell, 'directions': directions,
                            'source_frames': frames, 'output_native_size': size,
                            'preview_fps': 6, 'anchor': [.25, .75], 'pixels_per_unit': 24}
                if columns == 2:
                    metadata.update(columns=columns, rows=3)
                (root/'sheet.json').write_text(json.dumps(metadata))
                output = root/'finished'
                result = subprocess.run([sys.executable, str(SCRIPT), 'finish',
                    '--prepared', str(root), '--painted', str(root/'paint.png'),
                    '--output', str(output)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                for index, tile in enumerate(tiles):
                    name = f'{directions[index//3]}-{frames[index % 3]:04d}.png'
                    with Image.open(output/'sprites'/name) as exported:
                        self.assertEqual(exported.convert('RGBA').tobytes(), tile.tobytes())
                manifest = json.loads((output/'manifest.json').read_text())
                self.assertEqual(manifest['anchor'], [.25, .75])
                self.assertEqual(manifest['pixels_per_unit'], 24)
                self.assertEqual(manifest['fps'], 6)
                self.assertEqual(manifest['frames'], frames)
                self.assertEqual(manifest['directions'], directions)
                with Image.open(output/manifest['atlas']) as atlas:
                    for index, tile in enumerate(tiles):
                        x, y = (index % 3)*8, (index//3)*8
                        self.assertEqual(atlas.crop((x, y, x+8, y+8)).tobytes(), tile.tobytes())
                composition = root/'scene.json'
                composition.write_text(json.dumps({'size': [32, 24], 'frames': 3, 'fps': 6,
                    'background': '#34373d', 'assets': {'entity': 'finished'},
                    'instances': [{'asset': 'entity', 'direction': 'west', 'position': [10, 12]}]}))
                recording = root/'recording'
                composed = subprocess.run([sys.executable, str(SCRIPT.with_name('compose.py')),
                    '--config', str(composition), '--output', str(recording), '--no-gif'],
                    capture_output=True, text=True)
                self.assertEqual(composed.returncode, 0, composed.stderr)
                for phase in range(3):
                    expected = Image.new('RGBA', (32, 24), '#34373d')
                    expected.alpha_composite(tiles[phase+3], (8, 6))
                    with Image.open(recording/'frames'/f'{phase:04d}.png') as actual:
                        self.assertEqual(actual.tobytes(), expected.tobytes())
                report = json.loads((output/'boundary-report.json').read_text())
                self.assertEqual([entry['silhouette_iou'] for entry in report], [1]*6)
                with Image.open(output/'preview.webp') as preview:
                    self.assertEqual(preview.n_frames, 3)
                    for phase in range(3):
                        preview.seek(phase)
                        actual = preview.convert('RGBA')
                        self.assertEqual(actual.crop((0, 0, 8, 8)).tobytes(), tiles[phase].tobytes())
                        self.assertEqual(actual.crop((8, 0, 16, 8)).tobytes(), tiles[phase+3].tobytes())

    def test_legacy_sheet_requires_original_profile_and_preserves_cropped_anchor(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            Image.new('RGBA', (8, 8), 'red').save(root/'paint.png')
            Image.new('L', (8, 8), 255).save(root/'geometry-mask.png')
            (root/'sheet.json').write_text(json.dumps({
                'cell': [8, 8], 'crop': [10, 3, 18, 11], 'directions': ['south'],
                'source_frames': [1], 'output_native_size': [8, 8], 'preview_fps': 6}))
            output = root/'finished'
            command = [sys.executable, str(SCRIPT), 'finish', '--prepared', str(root),
                       '--painted', str(root/'paint.png'), '--output', str(output)]
            rejected = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn('sheet lacks placement metadata', rejected.stderr)
            self.assertFalse(output.exists())
            profile = root/'asset.json'
            profile.write_text(json.dumps({'size': [24, 20], 'anchor': [.5, .75],
                                          'pixels_per_unit': 24, 'shading': 'preserve'}))
            finished = subprocess.run(command+['--config', str(profile)], capture_output=True, text=True)
            self.assertEqual(finished.returncode, 0, finished.stderr)
            manifest = json.loads((output/'manifest.json').read_text())
            self.assertEqual(manifest['anchor'], [.25, 1.5])
            self.assertEqual(manifest['pixels_per_unit'], 24)

    def test_changed_aspect_is_rejected_before_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'sheet.json').write_text(json.dumps({
                'cell': [8, 8], 'source_frames': [1], 'output_native_size': [8, 8]}))
            Image.new('RGBA', (16, 8), 'red').save(root/'paint.png')
            output = root/'finished'
            result = subprocess.run([sys.executable, str(SCRIPT), 'finish',
                '--prepared', str(root), '--painted', str(root/'paint.png'),
                '--output', str(output)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('canvas aspect ratio changed', result.stderr)
            self.assertFalse(output.exists())

    def test_outline_preserves_paint_and_holes_and_keeps_raw_drift_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mask = Image.new('L', (8, 8))
            mask.paste(255, (1, 1, 7, 7))
            mask.save(root/'geometry-mask.png')
            paint = Image.new('RGBA', (8, 8), (35, 182, 211, 255))
            paint.putpixel((3, 3), (0, 0, 0, 0))
            paint.save(root/'paint.png')
            (root/'sheet.json').write_text(json.dumps({
                'cell': [8, 8], 'directions': ['south'], 'source_frames': [1],
                'output_native_size': [8, 8], 'preview_fps': 6,
                'anchor': [.5, .8], 'pixels_per_unit': 24}))
            output = root/'finished'
            result = subprocess.run([sys.executable, str(SCRIPT), 'finish',
                '--prepared', str(root), '--painted', str(root/'paint.png'),
                '--output', str(output), '--clip-to-geometry', '--outline', '112233'],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with Image.open(output/'sprites/south-0001.png') as exported:
                self.assertEqual(exported.getpixel((3, 3))[3], 0)
                for y in range(8):
                    for x in range(8):
                        if (x, y) == (3, 3):
                            continue
                        expected = (35, 182, 211, 255) if mask.getpixel((x, y)) else (17, 34, 51, 255)
                        self.assertEqual(exported.getpixel((x, y)), expected)
            report = json.loads((output/'boundary-report.json').read_text())[0]
            self.assertEqual(report['outside_pixels'], 28)
            self.assertEqual(report['missing_pixels'], 1)
            self.assertEqual(report['paint_outside_pixels'], 0)
            self.assertEqual(report['outline_pixels'], 28)
            self.assertEqual(report['exported_outside_pixels'], 28)
            self.assertEqual(json.loads((output/'manifest.json').read_text())['outline'], '112233')

    def test_geometry_clipping_removes_overshoot_without_filling_missing_paint(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mask = Image.new('L', (8, 8))
            mask.paste(255, (1, 1, 7, 7))
            mask.save(root/'geometry-mask.png')
            paint = Image.new('RGBA', (8, 8), (35, 182, 211, 255))
            paint.putpixel((3, 3), (17, 24, 31, 0))
            paint.save(root/'paint.png')
            (root/'sheet.json').write_text(json.dumps({
                'cell': [8, 8], 'directions': ['south'], 'source_frames': [1],
                'output_native_size': [8, 8], 'preview_fps': 6,
                'anchor': [.5, .8], 'pixels_per_unit': 24}))
            output = root/'finished'
            result = subprocess.run([sys.executable, str(SCRIPT), 'finish',
                '--prepared', str(root), '--painted', str(root/'paint.png'),
                '--output', str(output), '--clip-to-geometry'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with Image.open(output/'sprites/south-0001.png') as exported:
                for y in range(8):
                    for x in range(8):
                        expected = paint.getpixel((x, y)) if mask.getpixel((x, y)) and (x, y)!=(3, 3) else (0, 0, 0, 0)
                        self.assertEqual(exported.getpixel((x, y)), expected)
            report = json.loads((output/'boundary-report.json').read_text())[0]
            self.assertEqual(report['outside_pixels'], 28)
            self.assertEqual(report['missing_pixels'], 1)
            self.assertEqual(report['exported_outside_pixels'], 0)
            with Image.open(output/'silhouette-drift.png') as overlay:
                self.assertEqual(overlay.getpixel((0, 0)), (255, 55, 55, 255))
                self.assertEqual(overlay.getpixel((3, 3)), (0, 220, 255, 255))


if __name__ == '__main__':
    unittest.main()
