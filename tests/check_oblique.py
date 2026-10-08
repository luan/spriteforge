#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow>=12.1,<13"]
# ///
"""Test diagonal height projection, square ground and world-space surface normals."""
import hashlib
import math
from pathlib import Path
import subprocess
import tempfile
from PIL import Image

root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='spriteforge oblique ') as temporary:
    directory=Path(temporary)
    subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--python-exit-code','1',
                    '--python',str(root/'tests/oblique_fixture.py'),'--',str(directory)],check=True,capture_output=True)
    source=directory/'source.blend';digest=hashlib.sha256(source.read_bytes()).hexdigest()
    subprocess.run(['uv','run','--script',str(root/'skills/spriteforge/scripts/pipeline.py'),'render',
                    '--source',str(source),'--config',str(directory/'settings.json'),
                    '--output',str(directory/'render')],check=True,capture_output=True)
    # The ray at the projected sphere center sees a normal pointing at the camera.
    normal=[.5/math.sqrt(1.5),-.5/math.sqrt(1.5),1/math.sqrt(1.5)]
    linear=[(value+1)/2 for value in normal]
    expected=[round(255*(12.92*v if v<=.0031308 else 1.055*v**(1/2.4)-.055)) for v in linear]
    for frame,center in ((1,24),(2,16)):
        image=Image.open(directory/'render/sprites'/f'south-{frame:04d}.png').convert('RGBA')
        actual=image.getpixel((center,center))
        if actual[3]!=255 or any(abs(a-b)>4 for a,b in zip(actual,expected)):
            raise ValueError(f'height/world normal changed: frame {frame}, expected {expected}, got {actual}')
        for point,color in [((48,16),(128,144,96,255)),((32,16),(80,96,64,255)),
                            ((48,32),(80,96,64,255)),((48,48),(128,144,96,255))]:
            if image.getpixel(point)!=color:raise ValueError(f'ground grid changed at {point}')
        for x in range(25,40):
            stripe_color=(0,0,255,255) if (x-32)%2 else (255,0,0,255)
            if image.getpixel((x,48))!=stripe_color:raise ValueError(f'native pixels blended at {x}: {image.getpixel((x,48))}')
    if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:raise ValueError('source changed')
print('Passed: diagonal height, square ground, undeformed world normals, unblended native pixels, source preservation')
