#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow>=12.1,<13"]
# ///
"""Check baked paint, reuse, packed portability and input preservation."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/spriteforge/scripts'


def blender(script, *arguments):
    return subprocess.run(['blender', '--background', '--factory-startup',
        '--disable-autoexec', '--python-exit-code', '1', '--python', str(script),
        '--', *map(str, arguments)], capture_output=True, text=True)


def require_success(result):
    if result.returncode:
        raise ValueError(result.stdout + result.stderr)


def main():
    with tempfile.TemporaryDirectory(prefix='spriteforge paint ') as temporary:
        directory = Path(temporary)
        for name, mid, dark in [('red', (170,0,0), (68,0,0)), ('blue', (0,0,170), (0,0,68))]:
            image = Image.new('RGB', (16,16), mid)
            image.paste(dark, (0,0,8,16))
            image.save(directory / (name+'.png'))
        require_success(blender(ROOT/'tests/render_fixture.py', directory, '--paint-guide'))
        config = directory/'settings.json'
        settings = json.loads(config.read_text())
        settings['shading'] = 'preserve'
        config.write_text(json.dumps(settings))
        source = directory/'source.blend'
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        # Replacing overlapping/old UV layouts must preserve their paint input.
        require_success(blender(SCRIPTS/'bake_paint.py','--source',directory/'source.blend',
            '--config',config,'--maps',directory/'frozen maps','--output',directory/'frozen.blend',
            '--unwrap','--freeze','--resolution','64'))
        frozen = subprocess.run(['uv','run','--script',str(SCRIPTS/'pipeline.py'),'render',
            '--source',str(directory/'frozen.blend'),'--config',str(config),
            '--output',str(directory/'frozen render'),'--preview'],capture_output=True,text=True)
        require_success(frozen)
        with Image.open(directory/'frozen render/sprites/south-0001.png') as image:
            colors=set(image.convert('RGBA').get_flattened_data())
        if (68,0,0,255) not in colors or (0,0,170,255) not in colors or (170,0,0,255) in colors:
            raise ValueError('new paint islands changed the original UV input')
        require_success(blender(SCRIPTS/'bake_paint.py', '--source', source,
            '--config', config, '--maps', directory/'frozen maps',
            '--output', directory/'fixed reuse.blend', '--reuse',
            '--uv-source', directory/'frozen.blend', '--roles', 'red'))
        require_success(subprocess.run(['uv','run','--script',str(SCRIPTS/'pipeline.py'),'render',
            '--source',str(directory/'fixed reuse.blend'),'--config',str(config),
            '--output',str(directory/'fixed reuse render'),'--preview'],capture_output=True,text=True))
        with Image.open(directory/'frozen render/sprites/south-0001.png') as expected, \
             Image.open(directory/'fixed reuse render/sprites/south-0001.png') as actual:
            if actual.convert('RGBA').tobytes() != expected.convert('RGBA').tobytes():
                raise ValueError('reusing exact baked UVs changed the authored paint')
        changed = directory/'changed topology'
        changed.mkdir()
        for role in ('red', 'blue'):
            (changed/(role+'.png')).write_bytes((directory/(role+'.png')).read_bytes())
        require_success(blender(ROOT/'tests/render_fixture.py', changed,
                                '--paint-guide', '--reordered-topology'))
        rejected = blender(SCRIPTS/'bake_paint.py', '--source', changed/'source.blend',
            '--config', config, '--maps', directory/'frozen maps',
            '--output', changed/'reuse.blend', '--reuse', '--uv-source', directory/'frozen.blend')
        if rejected.returncode == 0 or 'Topology changed' not in rejected.stderr or (changed/'reuse.blend').exists():
            raise ValueError('incompatible topology was accepted for UV reuse')
        maps = directory/'paint maps'
        arguments = ['--source', source, '--config', directory/'settings.json',
                     '--maps', maps, '--resolution', '32','--form-guide']
        require_success(blender(SCRIPTS/'bake_paint.py', *arguments,
                                '--output', directory/'painted.blend'))
        paint = maps/'Painted surface.png'
        with Image.open(paint) as image:
            colors = [p for p in image.convert('RGBA').get_flattened_data() if p[3]]
        # A shaded guide must pass through the helper's transparent mix graph.
        if not (0 < max(p[0] for p in colors) < 68 and 0 < max(p[2] for p in colors) < 170):
            raise ValueError('form shading was not baked into both material regions')
        painted_bytes = paint.read_bytes()
        require_success(blender(SCRIPTS/'bake_paint.py', *arguments, '--reuse',
                                '--output', directory/'reused.blend'))
        if paint.read_bytes() != painted_bytes:
            raise ValueError('reuse changed the authored maps')
        collision = blender(SCRIPTS/'bake_paint.py', *arguments, '--reuse',
                            '--output', directory/'reused.blend')
        if collision.returncode == 0:
            raise ValueError('existing source output was overwritten')
        for texture in [paint, directory/'red.png', directory/'blue.png']:
            texture.unlink()
        result = subprocess.run(['uv', 'run', '--script', str(SCRIPTS/'pipeline.py'),
            'render', '--source', str(directory/'reused.blend'), '--config',
            str(directory/'settings.json'), '--output', str(directory/'render'),
            '--preview'], capture_output=True, text=True)
        require_success(result)
        if hashlib.sha256(source.read_bytes()).hexdigest() != before:
            raise ValueError('input source changed')
        # An inward-facing shell must not overwrite its exterior's UV paint.
        guides = []
        for variant, flag in [('exterior', '--exterior-guide'), ('shell', '--shell-guide')]:
            folder = directory / variant
            folder.mkdir()
            for role, color in [('red', (170,0,0)), ('blue', (0,0,170))]:
                Image.new('RGB', (16,16), color).save(folder/(role+'.png'))
            require_success(blender(ROOT/'tests/render_fixture.py', folder, '--paint-guide', flag))
            source = folder/'source.blend'
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            require_success(blender(SCRIPTS/'bake_paint.py', '--source', source,
                '--config', folder/'settings.json', '--output', folder/'painted.blend',
                '--maps', folder/'maps', '--resolution', '64', '--unwrap', '--form-guide'))
            with Image.open(folder/'maps/Painted surface.png') as image:
                guides.append(image.convert('RGBA').tobytes())
            if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
                raise ValueError('shell bake changed its input')
        if guides[0] != guides[1]:
            raise ValueError('underside overwrote exterior paint')
        inspection = subprocess.run(['uv', 'run', '--script', str(SCRIPTS/'pipeline.py'),
            'inspect', '--source', str(directory/'shell/painted.blend')], capture_output=True, text=True)
        require_success(inspection)
        surface = next(o for o in json.loads(inspection.stdout)['objects'] if o['name']=='Painted surface')
        if not any(m['type']=='SOLIDIFY' and m['viewport'] and m['render'] for m in surface['modifiers']):
            raise ValueError('paint bake removed or disabled the garment shell')
    print('Passed: form guide, exact UV reuse, incompatible topology rejection, material regions, packed portability, collision protection, exterior shell paint, input preservation')


if __name__ == '__main__':
    main()
