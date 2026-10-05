#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow>=12.1,<13"]
# ///
import json
from pathlib import Path
import random
import sys
import tempfile
import unittest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/spriteforge/scripts"))
from pixels import finish_image, validate_image
from settings import Settings
from style import SHADE_STOPS, soft_ramp


class PixelContractTests(unittest.TestCase):
    def setUp(self):
        self.config = {"size": [16, 20], "pixels_per_unit": 8,
                       "palette": {"cloth": ["112233", "aabbcc"]}}

    def load(self, data):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "asset.json"
            path.write_text(json.dumps(data))
            return Settings.load(path)

    def test_settings_reject_invalid_contracts(self):
        cases = [{"pixels_per_unit": v} for v in [0, -1, True, float("nan")]]
        cases += [{"frames": [2, 1]}, {"frames": [1, 1]}, {"directions": ["../escape"]},
                  {"size": [0, 16]}, {"size": [16.5, 20]}, {"anchor": [0.5, 2]},
                  {"palette": {"cloth": ["#112233"]}}, {"tileable": True},
                  {"light": [0, 0, 0]}, {"unexpected": True}]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.load({**self.config, **changes})

    def test_settings_round_trip_keeps_export_contract(self):
        settings = self.load({**self.config, "outline": None, "frames": [1, 3, 5], "anchor": [0.4, 0.7]})
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "asset.json"
            settings.save(path)
            self.assertEqual(settings, Settings.load(path))

    def test_soft_fill_preserves_material_hues(self):
        self.assertEqual(["66453a", "785144", "895d4d", "9b6c59", "ad7c65", "bb8a71", "c9987d"],
                         soft_ramp(["583a32", "825749", "ad7c65", "ce9d82"]))
        self.assertEqual((0, .12, .26, .4, .54, .68, .82), SHADE_STOPS)

    def test_finishing_locks_palette_alpha_and_native_contour(self):
        settings = self.load(self.config)
        rng = random.Random(42)
        for _ in range(25):
            image = Image.new("RGBA", settings.size)
            for x in range(5, 11):
                for y in range(5, 14):
                    image.putpixel((x, y), tuple(rng.randrange(256) for _ in range(3)) + (rng.choice([127, 128, 255]),))
            image.putpixel((8, 9), (255, 0, 0, 255))
            result = finish_image(image, settings)
            self.assertEqual(settings.size, result.size)
            validate_image(result, settings)
            self.assertEqual({0, 255}, {p[3] for p in result.get_flattened_data()})
            self.assertEqual(result.tobytes(), finish_image(image, settings).tobytes())

    def test_validation_rejects_empty_and_cropped_sprites(self):
        settings = self.load(self.config)
        for position in [None, (0, 5), (15, 5), (5, 0), (5, 19)]:
            image = Image.new("RGBA", settings.size)
            if position:
                image.putpixel(position, (17, 34, 51, 255))
            with self.subTest(position=position), self.assertRaises(ValueError):
                validate_image(finish_image(image, settings), settings)

    def test_ground_requires_opaque_matching_edges(self):
        settings = self.load({**self.config, "tileable": True, "outline": None})
        image = Image.new("RGBA", settings.size, (17, 34, 51, 255))
        self.assertTrue(validate_image(image, settings)["tileable"])
        for pixel in [(170, 187, 204, 255), (17, 34, 51, 0)]:
            changed = image.copy()
            changed.putpixel((0, 8), pixel)
            with self.subTest(pixel=pixel), self.assertRaises(ValueError):
                validate_image(changed, settings)


if __name__ == "__main__":
    unittest.main()
