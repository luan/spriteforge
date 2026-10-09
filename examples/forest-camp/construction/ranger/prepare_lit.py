#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow>=12.1,<13"]
# ///
"""Prepare full-RGB material fields at the human's projected texture density."""
import argparse
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageStat


def leather_panel(name: str) -> Image.Image:
    color = (52,62,70) if name == 'leggings' else (113,74,43) if name == 'satchel' else (102,65,39)
    image = Image.new('RGB', (128,128))
    for y in range(128):
        v = 1-y/127
        for x in range(128):
            u = x/127
            if name == 'leggings':
                factor = .93+.05*math.cos(x/128*math.tau*2)+.03*math.cos(y/128*math.pi*3)
            else:
                factor = .92+.08*math.cos(u*math.tau)+.035*math.cos(v*math.pi*3)
                factor += .12*math.exp(-((v-.88)/.023)**2)
                factor -= .16*math.exp(-((v-.13)/.025)**2)
            image.putpixel((x,y), tuple(round(c*factor) for c in color))
    if name in ('belt','strap','satchel'):
        draw = ImageDraw.Draw(image)
        for x in range(2,128,8):
            draw.line((x,15,x+3,15), fill=(174,136,88), width=1)
    return image


def prepare(atlas_path: Path, output: Path) -> None:
    with Image.open(atlas_path) as atlas:
        if atlas.width % 2 or atlas.height % 3 or atlas.width//2 != atlas.height//3:
            raise ValueError('The atlas must contain six equal square cells, two columns and three rows')
        side = atlas.width//2
        images = {name:atlas.crop(((i%2)*side,(i//2)*side,(i%2+1)*side,(i//2+1)*side))
                  .convert('RGB').resize((128,128), Image.Resampling.BOX)
                  for i,name in enumerate(('tunic','linen','boot','bracer','hair-cap','hair-lock'))}
    images['hair'] = images['hair-cap'].copy()
    for name in ('hair-cap','hair-lock'):
        images[name] = images[name].transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    for name in ('belt','strap','satchel','leggings'):
        images[name] = leather_panel(name)
    for name,source in [('boot-cuff','belt'),('skirt-front','tunic'),('skirt-back','tunic'),
                        ('sage','tunic'),('cream','linen'),('leather','bracer')]:
        images[name] = images[source].copy()
    # Match each UV axis to its projected coverage, rather than using square
    # maps for long narrow cloth, cuffs, straps and hair bundles.
    density={'tunic':(64,24),'linen':(48,16),'boot':(32,32),'bracer':(32,16),
             'hair-cap':(32,24),'hair-lock':(8,24),'hair':(32,24),
             'belt':(64,4),'strap':(4,32),'satchel':(24,24),'leggings':(48,24),
             'boot-cuff':(32,4),'skirt-front':(32,12),'skirt-back':(32,12),
             'sage':(64,24),'cream':(48,16),'leather':(32,16)}
    output.mkdir(parents=True, exist_ok=False)
    for name,image in images.items():
        if name in ('tunic','skirt-front','skirt-back','sage'):
            mean = ImageStat.Stat(image).mean
            target = (99,137,81)
            image = image.point([max(0,min(255,round(v*target[c]/mean[c])))
                                 for c in range(3) for v in range(256)])
        image=image.resize(density[name],Image.Resampling.BOX)
        image.save(output/(name+'.png'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--atlas', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.atlas, args.output)
