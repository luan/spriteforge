# Per-entity sheet painting

This optional route renders an entity's actual model and rig, then uses imagegen
to paint its complete sprite sheet. Generated paint can shift silhouettes and
interior features between poses. Review geometry and temporal consistency before
using the result; this route does not guarantee them.

## Prepare

From the installed skill:

```sh
uv run --script scripts/sheet_paint.py prepare \
  --source /path/to/walk.blend --config /path/to/walk.json \
  --step 2 --output /fresh/clay-sheet
```

The script copies the model, neutralizes material color while preserving authored
cutouts, and renders the same camera and rig at 4× resolution. It records cell
layout, source frames, placement and native silhouette masks in `sheet.json`.
`--step 2` selects every second pose and halves playback cadence to preserve the
source cycle duration; omit it to include every pose. Optional `--surface-guide`
adds `surface-sheet.png` with the original material colors and UV detail.

Prepare each entity independently. Terrain and water need reusable tile sheets
and their own frames; opaque tiles can use `opaque: true`. Assemble exported
atlases and manifests with `scripts/compose.py`, keeping placement, facing and
clip playback independent. A painted complete scene cannot supply those assets.

Inspect the sheet before editing. Give imagegen the exact canvas and cell layout
from `sheet.json`, the rendered sheet as geometry authority, and any concept or
game reference as art direction. Specify fixed silhouettes, joint positions,
equipment and transparent padding, consistent materials across every cell,
unrestricted RGB and connected pixel clusters at native size. Describe colors
explicitly when using clay. Establish proportions in the model before painting.
Keep the raw result, exact prompt and reference roles. Paint every modeled pose;
do not repeat one attractive pose as an animation.

## Export and review

```sh
uv run --script scripts/sheet_paint.py finish \
  --prepared /fresh/clay-sheet --painted /path/to/raw-painted.png \
  --output /fresh/paint-review
```

The finish step samples native PNGs and exports a held-pose lossless WebP,
`atlas.png` and a compositor-compatible `manifest.json`. The atlas has one row
per facing, regardless of the painting grid. Pixel density and placement anchors
survive cropping; figures are not recentered per pose. Older prepared sheets
without placement metadata require `--config` with the original render profile.

The boundary report compares generated coverage with Blender's model mask:
red overlay pixels exceed geometry; cyan pixels miss it. Coverage does not prove
matching joints, construction or temporal stability. Review all facings and the
full loop at native and integer zoom on light and dark backgrounds. Reject
misplaced feet, changing straps, crawling highlights and invented geometry.

For registered paint that covers the modeled surface, `--clip-to-geometry`
removes overshoot by intersecting paint coverage with the native silhouette. It
does not fill missing paint, move features or change retained visible colors.
The report still measures the raw paint before clipping. Reject misregistered
paint if clipping severs feet, straps or other features.

Use `--outline 242820` for a consistent one-native-pixel exterior contour after
clipping. It follows the retained sprite coverage and preserves interior colors
and holes. The report separates retained paint outside geometry
(`paint_outside_pixels`), added contour pixels (`outline_pixels`), and total
exported coverage outside geometry (`exported_outside_pixels`). Review the contour
with the rest of the asset set; ground tiles normally have no outer outline.

For static terrain states, add `--variants` to `finish`. Each state becomes its
own `variants/variant-NNNN/` atlas and manifest; `variants.json` lists them for
composition. Static variants have no animation preview and must not cycle as
frames. Review the native tiles together for seams and repetition.

Retain the model, rig, raw renders, frame mapping, paint inputs and outputs,
prompt, native sprites and review report. The final paint is on exported 2D
frames, not an editable 3D material. Model changes require a new render, paint
pass and visual review.
