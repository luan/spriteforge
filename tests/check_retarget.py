#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Exercise the public retarget CLI with loop/one-shot motion and preserved input."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/spriteforge'
BLENDER = ['blender', '--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1']


def main():
    source = SKILL / 'assets/humanoid.blend'
    before = hashlib.sha256(source.read_bytes()).digest()
    with tempfile.TemporaryDirectory(prefix='spriteforge motion ') as temporary:
        directory = Path(temporary)
        for clip, fps in [('Walk_Loop', 12), ('Walk_Loop', 11), ('Walk_Formal_Loop', 12), ('Jump_Start', 12)]:
            output = directory / f'{clip}-{fps}.blend'
            command = BLENDER + ['--python', str(SKILL / 'scripts/retarget.py'), '--',
                '--source', str(source), '--output', str(output), '--action', clip]
            if fps != 12:
                command += ['--fps', str(fps)]
            subprocess.run(command, check=True, capture_output=True)
            report = directory / f'{clip}-{fps}.json'
            subprocess.run(BLENDER + ['--python', str(ROOT / 'tests/motion_report.py'), '--',
                '--source', str(output), '--output', str(report)], check=True, capture_output=True)
            data = json.loads(report.read_text())
            if data['fps'] != fps or data['action']['Source clip'] != clip:
                raise ValueError('source timing or attribution lost')
            if data['action']['Loop']:
                first,closing=data['frames'][0],data['frames'][-1]
                if first['quaternions']!=closing['quaternions'] or first['locations']!=closing['locations']:
                    raise ValueError(clip+' closing pose differs')
            if clip == 'Walk_Loop':
                expected_count = round(40 * fps / 30)
                if data['range'] != [1, expected_count] or not data['action']['Loop']:
                    raise ValueError('walk duration changed')
                if abs(expected_count / fps - 40 / 30) > .5 / fps:
                    raise ValueError('walk duration rounded beyond half a pose interval')
                if max(abs(f['ground_min']) for f in data['frames']) > .025:
                    raise ValueError('retargeted base has lost its floor reference')
                if not 1.8 < data['action']['Travel speed'] < 2.1:
                    raise ValueError('source-derived movement speed lost')
                for bone in ['thigh.L', 'thigh.R', 'upperarm.L', 'upperarm.R']:
                    if len({tuple(f['quaternions'][bone]) for f in data['frames']}) < 12:
                        raise ValueError(f'motion missing on {bone}')
            elif clip=='Jump_Start' and (data['action']['Loop'] or data['frames'][0]['quaternions'] == data['frames'][-2]['quaternions']):
                raise ValueError('one-shot endpoint was treated as a loop')
            saved = hashlib.sha256(output.read_bytes()).digest()
            refused = subprocess.run(command, capture_output=True)
            if refused.returncode == 0 or hashlib.sha256(output.read_bytes()).digest() != saved:
                raise ValueError('existing output was overwritten')
    if hashlib.sha256(source.read_bytes()).digest() != before:
        raise ValueError('authored source changed')
    print('Passed: walk timing, moving limbs, closing pose, floor reference, source speed, one-shot endpoint, input preservation, output collision, paths with spaces')


if __name__ == '__main__':
    main()
