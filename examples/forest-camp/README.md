# Forest camp

An original scene assembled from 19 independent sprite assets. Ground tiles are
64px; the ranger occupies roughly 64px vertically. All assets share 24 pixels per
world unit. Walking uses 6 held poses per second, idle 3, and environment clips 6.
The composition records at 12fps.

![Animated forest camp](media/scene.webp)

[24-second video](media/scene.mp4) · [Full scene PNG](media/scene.png)
· [Four-direction character animation](media/ranger.webp)

## Replay from a clean checkout

Requires `uv` and Blender 5.2+. Add `--mp4` when FFmpeg is installed. Choose a
fresh output directory; the example's published files remain inputs.

```sh
uv run --script examples/forest-camp/rebuild.py \
  --output /tmp/spriteforge-forest-camp --verify --mp4
```

This renders each source independently, prepares modeled pose sheets, replays
the saved per-entity paint edits, exports native atlases and records the scene.
`--verify` compares every atlas's coverage and visible RGB pixels with the
published assets. New designs need their own modeling and painting work.

To record a new layout using the existing exported sprites:

```sh
uv run --script skills/spriteforge/scripts/compose.py \
  --config examples/forest-camp/scene.json \
  --output /tmp/spriteforge-camp-recording --no-gif --mp4
```

Serve the repository to inspect individual sprites, facings and Blender poses:

```sh
uv run --no-project python -m http.server 8000 --bind 127.0.0.1
```

Open [the interactive viewer](http://127.0.0.1:8000/examples/forest-camp/).

## Author the forest and ranger from inputs

```sh
uv run --script examples/forest-camp/construction/build.py \
  --output /tmp/spriteforge-camp-models
```

The forest recipe constructs the trees, foliage, terrain transitions, pond and
separate ripple geometry from UV fields. The ranger recipe starts with the
skill's bundled CC0 anatomical base, constructs fitted clothing and equipment,
authors UV materials, calibrates the actual model height, retargets a licensed
walk and adds breathing and a modeled blink. Both retain editable geometry,
materials and animation. Other entities are provided as packed editable model
inputs to the exact replay above.

## Files

- `assets/`: individual native PNGs, atlases and runtime manifests.
- `models/`: packed Blender geometry, UV maps, rigs and clips.
- `profiles/` and `recipes.json`: rendering, sampling and finishing settings.
- `paint/`: per-entity paint inputs, prompts, modeled guides and coverage masks.
- `construction/`: forest and ranger geometry recipes and their UV inputs.
- `scene.json`: independent placement, facing, clip phase and depth ordering.
- `media/`: a four-second lossless scene excerpt, full video and character loop.

The ranger includes four walking and idle facings. The copperback beetle example
uses its east-facing idle sheet. Ground and pond depth remain static; ripple
geometry animates separately. Fixed model surfaces on the idle ranger and chest
hold their paint while moving surfaces retain their own poses.

These are original assets. The [Blender Studio anatomical base](../../skills/spriteforge/assets/humanoid-license.md)
and [Quaternius animation library](../../skills/spriteforge/assets/animation-license.md)
retain their CC0 source attribution.
