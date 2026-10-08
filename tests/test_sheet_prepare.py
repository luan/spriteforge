#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow>=12.1,<13"]
# ///
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT/'skills/spriteforge'


@unittest.skipUnless(shutil.which('blender'), 'requires Blender 5.2+')
class SheetPrepareTests(unittest.TestCase):
    def test_guides_preserve_authored_cutouts_and_full_ground_coverage(self):
        for opaque in (False, True):
            with self.subTest(opaque=opaque), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                model = root/'model.blend'
                command = ['blender', '--background', '--factory-startup', '--disable-autoexec',
                           '--python-exit-code', '1', '--python', str(ROOT/'tests/fixtures/sheet_source.py'),
                           '--', '--skill', str(SKILL), '--output', str(model)]
                if opaque:
                    command.append('--opaque')
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                digest = hashlib.sha256(model.read_bytes()).hexdigest()
                config = {'size': [96, 96], 'pixels_per_unit': 20, 'collection': 'Fixture',
                          'frames': [1], 'directions': ['south'], 'fps': 6, 'anchor': [.5, .65],
                          'shear': [-.45, 1.1], 'outline': None, 'opaque': opaque,
                          'shading': 'preserve', 'lighting': 'studio'}
                (root/'asset.json').write_text(json.dumps(config))
                prepared = root/'prepared'
                result = subprocess.run(['uv', 'run', '--script', str(SKILL/'scripts/sheet_paint.py'),
                    'prepare', '--source', str(model), '--config', str(root/'asset.json'),
                    '--surface-guide', '--output', str(prepared)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertEqual(hashlib.sha256(model.read_bytes()).hexdigest(), digest)
                metadata = json.loads((prepared/'sheet.json').read_text())
                self.assertEqual(metadata['source_sha256'], digest)
                self.assertEqual(json.loads((prepared/'clay.json').read_text())['opaque'], opaque)
                with Image.open(prepared/'clay-sheet.png') as clay, Image.open(prepared/'surface-sheet.png') as color:
                    self.assertEqual(clay.size, color.size)
                    self.assertEqual(clay.getchannel('A').tobytes(), color.getchannel('A').tobytes())
                    self.assertIsNotNone(ImageChops.difference(clay.convert('RGB'), color.convert('RGB')).getbbox())
                with Image.open(prepared/'render/sprites/south-0001.png') as native:
                    alpha = native.getchannel('A')
                    if opaque:
                        self.assertEqual(alpha.getextrema(), (255, 255))
                    else:
                        self.assertEqual(alpha.getextrema(), (0, 255))


if __name__ == '__main__':
    unittest.main()
