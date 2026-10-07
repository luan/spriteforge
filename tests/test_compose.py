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
    def test_webp_recording_retains_full_rgb_frames(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            atlas=Image.new('RGBA',(64,32))
            for y in range(32):
                for x in range(64):atlas.putpixel((x,y),(x*3,y*7,91,255))
            atlas.save(root/'atlas.png')
            (root/'manifest.json').write_text(json.dumps({'frames':[1,2],'fps':12,
                'directions':['south'],'size':[32,32],'anchor':[.5,.5],
                'pixels_per_unit':16,'atlas':'atlas.png'}))
            config=root/'scene.json'
            config.write_text(json.dumps({'size':[32,32],'frames':2,'fps':12,
                'assets':{'actor':'.'},'instances':[{'asset':'actor','position':[16,16]}]}))
            record(config,root/'recording',False,gif=False)
            self.assertFalse((root/'recording/scene.gif').exists())
            with Image.open(root/'recording/scene.webp') as animation:
                self.assertEqual(animation.n_frames,2)
                for frame in range(2):
                    animation.seek(frame)
                    with Image.open(root/'recording/frames'/f'{frame:04d}.png') as expected:
                        self.assertEqual(animation.convert('RGB').tobytes(),expected.convert('RGB').tobytes())
                        self.assertGreater(len(set(expected.get_flattened_data())),256)

    def test_route_uses_ground_speed_and_turns_to_each_facing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            colors = ['red', 'green', 'blue', 'yellow']
            atlas = Image.new('RGBA', (2,8))
            for row,color in enumerate(colors):atlas.paste(color,(0,row*2,2,row*2+2))
            atlas.save(root/'atlas.png')
            (root/'manifest.json').write_text(json.dumps({'frames':[1],'fps':1,
                'directions':['east','south','west','north'],'size':[2,2],
                'anchor':[.5,.5],'pixels_per_unit':16,'atlas':'atlas.png'}))
            points=[[4,4],[12,4],[12,12],[4,12]]
            config=root/'scene.json'
            config.write_text(json.dumps({'size':[20,20],'frames':5,'fps':1,
                'assets':{'actor':'.'},'instances':[{'asset':'actor','position':points[0],
                    'route':points,'speed':8}]}))
            record(config,root/'recording',False)
            for index,(position,color) in enumerate(zip(points+[points[0]],colors+[colors[0]])):
                with Image.open(root/'recording/frames'/f'{index:04d}.png') as image:
                    self.assertEqual(image.getpixel(tuple(position)),Image.new('RGBA',(1,1),color).getpixel((0,0)))

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
