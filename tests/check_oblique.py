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
        if image.getpixel((12,48))!=(0,0,255,255) or image.getpixel((20,48))[3]!=0:
            raise ValueError('authored paint changed its color or lost cutout alpha')
    if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:raise ValueError('source changed')
    visibility_source=directory/'visibility.blend'
    visibility_digest=hashlib.sha256(visibility_source.read_bytes()).hexdigest()
    subprocess.run(['uv','run','--script',str(root/'skills/spriteforge/scripts/pipeline.py'),'render',
                    '--source',str(visibility_source),'--config',str(directory/'visibility.json'),
                    '--output',str(directory/'visibility')],check=True,capture_output=True)
    image=Image.open(directory/'visibility/sprites/south-0001.png').convert('RGBA')
    if image.getpixel((90,40))[3]!=0:raise ValueError('camera-hidden caster became visible')
    shadowed=image.getpixel((33,64));clear=image.getpixel((95,64))
    if shadowed[3]!=255 or clear[3]!=255 or max(c-s for c,s in zip(clear[:3],shadowed[:3]))<25:
        raise ValueError(f'authored shadow visibility changed: shadowed {shadowed}, clear {clear}')
    if hashlib.sha256(visibility_source.read_bytes()).hexdigest()!=visibility_digest:
        raise ValueError('visibility source changed')
print('Passed: diagonal projection, world normals, native pixels, paint alpha, camera/shadow visibility, source preservation')
