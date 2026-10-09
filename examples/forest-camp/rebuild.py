#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow>=12.1,<13"]
# ///
"""Replay the demo's per-entity renders and paint edits, then record its scene."""
import argparse
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageChops


def main() -> None:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--skill', type=Path, default=here.parents[1]/'skills/spriteforge')
    parser.add_argument('--blender', default='blender')
    parser.add_argument('--verify', action='store_true', help='compare every replayed atlas with the published native pixels')
    parser.add_argument('--mp4', action='store_true', help='also record video with FFmpeg')
    args = parser.parse_args()
    output, skill = args.output.resolve(), args.skill.resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output/'logs').mkdir()

    def run(name: str, arguments: list[str]) -> None:
        log = output/'logs'/f'{name}.log'
        print(name, flush=True)
        with log.open('w') as stream:
            subprocess.run(arguments, stdout=stream, stderr=subprocess.STDOUT, check=True)

    for name, recipe in json.loads((here/'recipes.json').read_text()).items():
        destination = output/'assets'/name
        source, profile = here/recipe['source'], here/recipe['profile']
        if recipe['method'] == 'sheet-paint':
            prepared = output/'prepared'/name
            arguments = ['uv', 'run', '--script', str(skill/'scripts/sheet_paint.py'), 'prepare',
                         '--source', str(source), '--config', str(profile), '--output', str(prepared),
                         '--blender', args.blender, '--step', str(recipe['step']), '--surface-guide']
            if recipe['stationary']:
                arguments.append('--hold-stationary-surfaces')
            run(name+'-prepare', arguments)
            arguments = ['uv', 'run', '--script', str(skill/'scripts/sheet_paint.py'), 'finish',
                         '--prepared', str(prepared), '--painted', str(here/recipe['paint']),
                         '--output', str(destination), '--clip-to-geometry']
            if recipe['register']:
                arguments.append('--register')
            if recipe['outline']:
                arguments.extend(['--outline', recipe['outline']])
            run(name+'-paint', arguments)
        else:
            run(name+'-render', ['uv', 'run', '--script', str(skill/'scripts/pipeline.py'), 'render',
                                '--source', str(source), '--config', str(profile),
                                '--output', str(destination), '--blender', args.blender])
        if args.verify:
            with Image.open(destination/'atlas.png') as actual, Image.open(here/'assets'/name/'atlas.png') as expected:
                if actual.size != expected.size:
                    raise ValueError(name+': replayed atlas size changed')
                actual, expected = actual.convert('RGBA'), expected.convert('RGBA')
                if ImageChops.difference(actual.getchannel('A'), expected.getchannel('A')).getbbox():
                    raise ValueError(name+': replayed coverage changed')
                difference = ImageChops.difference(actual.convert('RGB'), expected.convert('RGB'))
                if ImageChops.multiply(difference, expected.getchannel('A').convert('RGB')).getbbox():
                    raise ValueError(name+': replayed visible colors changed')

    scene = json.loads((here/'scene.json').read_text())
    (output/'scene.json').write_text(json.dumps(scene, indent=2)+'\n')
    arguments = ['uv', 'run', '--script', str(skill/'scripts/compose.py'),
                 '--config', str(output/'scene.json'), '--output', str(output/'recording'), '--no-gif']
    if args.mp4:
        arguments.append('--mp4')
    run('recording', arguments)
    print(output/'recording/scene.webp')


if __name__ == '__main__':
    main()
