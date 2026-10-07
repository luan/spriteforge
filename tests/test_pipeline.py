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
                  {"light": [0, 0, 0]}, {"unexpected": True}, {"opaque": True}, {"opaque": 1}]
        cases += [{'supersample':v} for v in (0,9,True,1.5)]
        cases += [{'cluster_materials':['missing']}, {'cluster_materials':'cloth'}]
        cases += [{'size':[4096,4096],'supersample':4}]
        cases += [{'lighting':'unknown'}, {'lighting':'studio','shear':[.3,.8]}]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.load({**self.config, **changes})

    def test_settings_round_trip_keeps_export_contract(self):
        settings = self.load({**self.config, "outline": None, "frames": [1, 3, 5], "anchor": [0.4, 0.7],
                              "lighting":"studio"})
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "asset.json"
            settings.save(path)
            self.assertEqual(settings, Settings.load(path))

    def test_soft_fill_preserves_material_hues(self):
        self.assertEqual(["66453a", "785144", "895d4d", "9b6c59", "ad7c65", "bb8a71", "c9987d"],
                         soft_ramp(["583a32", "825749", "ad7c65", "ce9d82"]))
        self.assertEqual((0, .12, .26, .4, .54, .68, .82), SHADE_STOPS)

    def test_finishing_preserves_source_colors_alpha_and_native_contour(self):
        settings = self.load(self.config)
        rng = random.Random(42)
        for _ in range(25):
            image = Image.new("RGBA", settings.size)
            for x in range(5, 11):
                for y in range(5, 14):
                    image.putpixel((x, y), tuple(rng.randrange(256) for _ in range(3)) + (rng.choice([127, 128, 255]),))
            image.putpixel((8, 9), (255, 0, 0, 255))
            result = finish_image(image, settings)
            self.assertEqual((255,0,0,255), result.getpixel((8,9)))
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

    def test_opaque_ground_accepts_unique_edges_and_rejects_holes(self):
        settings = self.load({**self.config, "opaque": True, "outline": None})
        image = Image.new("RGBA", settings.size, (80, 120, 45, 255))
        image.putpixel((0, 0), (130, 90, 60, 255))
        validate_image(finish_image(image, settings), settings)
        image.putpixel((8, 9), (80, 120, 45, 0))
        with self.assertRaises(ValueError):
            validate_image(finish_image(image, settings), settings)

    def test_coverage_integrates_subpixel_detail_without_phase_flicker(self):
        settings = self.load({**self.config,'outline':None,'supersample':4})
        dark, light = (17,34,51,255),(170,187,204,255)
        results = []
        for phase in range(4):
            image = Image.new('RGBA',(64,80),dark)
            for y in range(0,80,4):
                for x in range(0,64,4): image.putpixel((x+phase,y+phase),light)
            results.append(finish_image(image,settings).tobytes())
        self.assertEqual([results[0]]*4,results)
        color = Image.frombytes('RGBA',settings.size,results[0]).getpixel((8,8))
        self.assertTrue(all(a < c < b for a,c,b in zip(dark[:3],color[:3],light[:3])))

    def test_export_preserves_more_than_256_colors_without_a_palette(self):
        settings = self.load({'size':[24,24],'pixels_per_unit':8,'outline':None})
        image = Image.new('RGBA',settings.size)
        for y in range(2,22):
            for x in range(2,22):
                image.putpixel((x,y),(x*10,y*10,(x+y)*5,255))
        result = finish_image(image,settings)
        validate_image(result,settings)
        self.assertEqual(image.tobytes(),result.tobytes())
        self.assertGreater(len({p[:3] for p in result.get_flattened_data() if p[3]}),256)

    def test_transparent_rgb_does_not_tint_covered_edge_pixels(self):
        settings = self.load({'size':[16,20],'pixels_per_unit':8,'outline':None,'supersample':4})
        image = Image.new('RGBA',(64,80),(255,0,0,0))
        image.paste((120,180,240,255),(20,20,23,24))
        self.assertEqual((120,180,240,255),finish_image(image,settings).getpixel((5,5)))

    def test_surface_clusters_preserve_focal_accents_and_supported_detail(self):
        settings = self.load({**self.config,'outline':None,'cluster_materials':['cloth'],
            'palette':{'cloth':['112233','aabbcc'],'pin':['ffcc33']}})
        image = Image.new('RGBA',settings.size)
        image.paste((17,34,51,255),(2,3,14,18))
        image.putpixel((4,5),(170,187,204,255))
        image.putpixel((2,7),(170,187,204,255))
        image.putpixel((8,9),(255,204,51,255))
        for xy in ((10,12),(11,12),(10,13),(11,13)):image.putpixel(xy,(170,187,204,255))
        result = finish_image(image,settings)
        self.assertEqual((17,34,51,255),result.getpixel((4,5)))
        self.assertEqual((255,204,51,255),result.getpixel((8,9)))
        self.assertEqual((170,187,204,255),result.getpixel((2,7)))
        self.assertEqual(image.getchannel('A').tobytes(),result.getchannel('A').tobytes())
        for xy in ((10,12),(11,12),(10,13),(11,13)):
            self.assertEqual((170,187,204,255),result.getpixel(xy))
        shared = self.load({**self.config,'outline':None,'cluster_materials':['cloth'],
            'palette':{'cloth':['112233','aabbcc'],'pin':['aabbcc']}})
        self.assertEqual((170,187,204,255),finish_image(image,shared).getpixel((4,5)))

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
