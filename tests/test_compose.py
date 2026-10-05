#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow>=12.1,<13"]
# ///
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/spriteforge/scripts"))
from compose import record


class RecordingTests(unittest.TestCase):
    def test_native_anchor_and_actual_frame_timing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            atlas = Image.new("RGBA", (32, 16), "red")
            atlas.paste("blue", (16, 0, 32, 16))
            atlas.save(root / "atlas.png")
            (root / "manifest.json").write_text(json.dumps({
                "frames": [1, 2], "fps": 12, "directions": ["south"],
                "size": [16, 16], "anchor": [.5, .75],
                "pixels_per_unit": 16, "atlas": "atlas.png"}))
            config = root / "scene.json"
            config.write_text(json.dumps({"size": [32, 32], "frames": 2,
                "assets": {"actor": "."}, "instances": [
                    {"asset": "actor", "position": [16, 20]}]}))
            output = root / "recording"
            record(config, output, False)
            with Image.open(output / "frames/0000.png") as first:
                self.assertEqual(first.getpixel((8, 8)), (255, 0, 0, 255))
                self.assertNotEqual(first.getpixel((7, 8)), (255, 0, 0, 255))
            with Image.open(output / "frames/0001.png") as second:
                self.assertEqual(second.getpixel((8, 8)), (0, 0, 255, 255))
            self.assertEqual(json.loads((output / "manifest.json").read_text())["fps"], 12)
            settings = json.loads(config.read_text())
            settings["fps"] = 24
            settings["frames"] = 4
            config.write_text(json.dumps(settings))
            record(config, root / "held", False)
            colors = []
            for index in range(4):
                with Image.open(root / "held" / "frames" / f"{index:04d}.png") as image:
                    colors.append(image.getpixel((8, 8)))
            self.assertEqual(colors, [(255, 0, 0, 255)] * 2 + [(0, 0, 255, 255)] * 2)
            settings["fps"] = 6
            config.write_text(json.dumps(settings))
            with self.assertRaisesRegex(ValueError, "skip animation poses"):
                record(config, root / "mismatch", False)
            self.assertFalse((root / "mismatch").exists())


if __name__ == "__main__":
    unittest.main()
