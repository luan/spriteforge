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

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/spriteforge/scripts"


class StaticVariantsTests(unittest.TestCase):
    def test_variants_keep_facings_and_never_cycle_between_material_states(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            colors = ["#794425", "#38674a", "#37698d", "#ad8647"]
            sheet = Image.new("RGBA", (16, 16))
            for index, color in enumerate(colors):
                sheet.paste(
                    color,
                    (
                        (index % 2) * 8,
                        (index // 2) * 8,
                        (index % 2 + 1) * 8,
                        (index // 2 + 1) * 8,
                    ),
                )
            sheet.save(root / "paint.png")
            sheet.getchannel("A").save(root / "geometry-mask.png")
            (root / "sheet.json").write_text(
                json.dumps(
                    {
                        "directions": ["south", "west"],
                        "source_frames": [1, 7],
                        "cell": [8, 8],
                        "columns": 2,
                        "output_native_size": [16, 16],
                        "preview_fps": 6,
                        "pixels_per_unit": 24,
                        "anchor": [0.5, 0.5],
                    }
                )
            )
            output = root / "exports"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "sheet_paint.py"),
                    "finish",
                    "--prepared",
                    str(root),
                    "--painted",
                    str(root / "paint.png"),
                    "--variants",
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((output / "manifest.json").exists())
            self.assertFalse((output / "preview.webp").exists())
            assets = json.loads((output / "variants.json").read_text())["assets"]
            self.assertEqual(list(assets), ["variant-0001", "variant-0007"])
            for frame, relative in zip([1, 7], assets.values()):
                manifest = json.loads((output / relative / "manifest.json").read_text())
                self.assertEqual(manifest["frames"], [frame])
                self.assertEqual(manifest["directions"], ["south", "west"])
                self.assertEqual(manifest["anchor"], [0.5, 0.5])
            config = {
                "size": [16, 8],
                "fps": 6,
                "frames": 3,
                "assets": assets,
                "instances": [
                    {"asset": "variant-0001", "position": [4, 4], "direction": "west"},
                    {
                        "asset": "variant-0007",
                        "position": [12, 4],
                        "direction": "south",
                    },
                ],
            }
            (output / "scene.json").write_text(json.dumps(config))
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "compose.py"),
                    "--config",
                    str(output / "scene.json"),
                    "--output",
                    str(root / "recording"),
                    "--no-gif",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            expected = Image.new("RGBA", (16, 8), colors[2])
            expected.paste(colors[1], (8, 0, 16, 8))
            for frame in range(3):
                with Image.open(
                    root / "recording/frames" / f"{frame:04d}.png"
                ) as actual:
                    self.assertEqual(actual.tobytes(), expected.tobytes())


if __name__ == "__main__":
    unittest.main()
