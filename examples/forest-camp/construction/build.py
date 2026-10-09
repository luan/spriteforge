#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Construct the forest and rigged ranger from geometry code and UV inputs."""
import argparse
from pathlib import Path
import subprocess


def main() -> None:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--skill', type=Path, default=here.parents[2]/'skills/spriteforge')
    parser.add_argument('--blender', default='blender')
    args = parser.parse_args()
    skill, output = args.skill.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    logs = output/'logs'
    logs.mkdir()
    ranger = output/'ranger'
    ranger.mkdir()
    scripts = here/'ranger'

    def run(name: str, command: list[str]) -> None:
        print(name, flush=True)
        with (logs/f'{name}.log').open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)

    def blender(name: str, script: Path, *arguments: str | Path) -> None:
        run(name, [args.blender, '--background', '--factory-startup', '--disable-autoexec',
                   '--python-exit-code', '1', '--python', str(script), '--', *map(str, arguments)])

    blender('forest', here/'forest.py', '--skill', skill, '--maps', here/'maps/forest',
            '--output', output/'forest.blend')
    run('ranger-materials', ['uv', 'run', '--script', str(scripts/'prepare_lit.py'),
                            '--atlas', str(scripts/'material-atlas.png'), '--output', str(ranger/'textures')])
    blender('ranger-model', scripts/'author.py', '--skill', skill, '--output', ranger)
    blender('ranger-standing', scripts/'standing.py', '--source', ranger/'mira-source.blend',
            '--output', ranger/'standing.blend')
    blender('ranger-size', scripts/'calibrate.py', '--skill', skill,
            '--source', ranger/'standing.blend', '--output', ranger/'calibrated.blend', '--height', '64')
    blender('ranger-surface', scripts/'lit.py', '--skill', skill, '--source', ranger/'calibrated.blend',
            '--textures', ranger/'textures', '--output', ranger/'textured.blend')
    blender('ranger-motion', skill/'scripts/retarget.py', '--source', ranger/'textured.blend',
            '--output', ranger/'retargeted.blend', '--action', 'Walk_Formal_Loop', '--fps', '12')
    blender('ranger-walk', scripts/'refine.py', '--source', ranger/'retargeted.blend',
            '--output', output/'ranger-walk.blend', '--head-lift', '25')
    blender('ranger-idle', scripts/'idle.py', '--source', ranger/'textured.blend',
            '--output', output/'ranger-idle.blend')
    print(output)


if __name__ == '__main__':
    main()
