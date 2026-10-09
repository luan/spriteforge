# Rendering workflow

Keep concepts, authoring scripts, textured sources, motion refinement and
recorded scenes with delivered assets. Review their source/sprite pairs at the
requested native size; measured export checks do not establish art quality.

Requirements: Blender 5.2+ and `uv`. The launcher's inline metadata requires
Python 3.10+ and Pillow 12; `uv` provisions them automatically. Blender's embedded
Python evaluates scenes; the `uv` environment finishes PNGs. No Aseprite, FFmpeg,
or Blender plugin is required.

From this skill directory:

```sh
uv run --script scripts/pipeline.py inspect --source /path/to/model.blend
uv run --script scripts/pipeline.py review --source /path/to/model.blend \
  --config /path/to/asset.json --output /path/to/model-review
uv run --script scripts/pipeline.py render --source /path/to/model.blend \
  --config /path/to/asset.json --output /path/to/preview-run --preview
uv run --script scripts/pipeline.py render --source /path/to/model.blend \
  --config /path/to/asset.json --output /path/to/full-run
```

Use `--blender /path/to/blender` if Blender is not on PATH. Paths containing
spaces are supported. Output directories must not exist. Failed runs remain
available with their raw images and settings; choose a new directory on retry.

`review` checks the 3D source before pixel finishing. It renders four physical
camera views at four evenly spaced configured poses, both with neutral studio
shading and the original materials. `clay-review.png` exposes construction and
deformation; `paint-review.png` exposes surface coverage. Individual PNGs,
`inspection.json` and a source-hash manifest are retained. This command always
reviews all four directions; `--preview` only limits sprite rendering.

## Asset settings

```json
{
  "collection": "Character",
  "size": [128, 128],
  "pixels_per_unit": 24,
  "directions": ["east", "north", "west", "south"],
  "frames": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
  "fps": 12,
  "pivot": [0, 0, 0],
  "anchor": [0.75, 0.75],
  "shear": [0, 0.85],
  "light": [-0.5, -0.65, 1],
  "outline": null,
  "shading": "preserve",
  "lighting": "studio",
  "tileable": false,
  "supersample": 1,
  "cluster_materials": []
}
```

`size` and `pixels_per_unit` are required. The example uses an actor canvas and anchor; select them for the asset bounds.
Collection defaults to all renderable geometry, frames to `[1]`, and shading to
`preserve`. Select `bands` explicitly for untextured studies.
Use `preserve` for finished authored materials. Exported frames have equal durations even when source
frame numbers have gaps.

- `collection` selects an asset including descendants and collection instances.
  Hide unrelated floors or select a specific collection.
- `size` is the native PNG cell. Rectangular cells are valid.
- `pixels_per_unit` sets shared world scale. Increasing the canvas makes room
  without shrinking the asset. Match density across world assets.
- `pivot` is a fixed world-space origin before direction rotation. Use the feet
  for actors. `anchor` locates it in normalized image coordinates from the
  top-left. Neither changes between frames.
- `directions`: East 90°, North 180°, West 270°, South 0°. Models face -Y in
  the south view; correct a different forward axis in the authored asset.
- `shear` defines the oblique projection: after rotation, screen
  X = X + shear[0] × Z and screen Y = Y + shear[1] × Z.
  Ground stays square and height follows the chosen shear vector. This artistic projection is
  not an isometric projection. `[0,0]` gives a top-down view.
- `lighting: studio` uses a tilted physical orthographic camera with pixel-aspect
  correction. Ground remains square and the actual geometry/normals drive warm
  key, cool fill and rim lighting. It requires `shear[0] = 0`. Use with textured
  `lit_material` surfaces; unlit emissions remain unlit. `lighting: key` retains
  the earlier projected-proxy renderer and supports arbitrary diagonal shear.
- `preserve` retains source materials and their full RGB colors. Pack texture
  images or retain accessible files. Prefer UV mapping: Generated/world
  coordinates can change when render proxies are projected.
- `palette` is optional and supplies material color ramps for the explicit
  `bands` geometry-study mode and the form-guide helper. It never restricts
  exported texture colors. There is no per-material or total color-count cap.
- `outline` adds a one-pixel outer contour; null disables it. Non-ground sprites
  need at least two transparent pixels around the finished contour.
- `tileable` requires full opacity, no outline, and exactly matching opposite
  edge pixels. This is a conservative border contract: continuous textures can
  be visually seamless without identical boundary samples. Set it false for
  those textures and review repetition manually.
- `opaque: true` is for a complete nonrepeating ground patch. It requires full
  opacity and `outline: null`, permits different border colors and skips the
  transparent sprite margin. Keep it false for actors, props and vegetation.

- `supersample` renders 1–8 samples across each native pixel dimension; default
  1. Native sampling retains sharp painted boundaries. Values above 1 opt into
  coverage averaging in premultiplied RGBA, which softens texture boundaries;
  compare the result at native size before using it. Finishing makes alpha
  binary and preserves full RGB rather than quantizing it.
  Coverage grid dimensions are limited to 8192; larger native cells need a
  smaller factor until tiled rendering is supported.
- `cluster_materials` names main surface palette roles. Their one- and two-pixel
  interior shade regions join supported neighboring regions of at least three
  pixels. Silhouette pixels stay intact. Colors present in unlisted roles are
  protected, including shared colors; use distinct colors for focal accents.
  The default and style preset lists are empty. This is optional cleanup;
  compare against unmodified paint before using it. Keep the list consistent
  when changing palette names.

The renderer produces the native cell, or an explicitly requested coverage grid. Finishing
reduces that grid when needed,
keeps binary alpha and full RGB colors, applies any explicitly requested shade cleanup,
and adds the optional contour. Previews enlarge with nearest-neighbor sampling.
Do not blur or smooth the delivered PNGs or interpolate animation poses.

Studio mode accumulates 32 EEVEE lighting samples with a narrow reconstruction
filter. This is separate from `supersample`, which changes render resolution.
For nonzero horizontal shear it instead casts native Cycles oblique rays with
128 fixed-seed samples and no denoising. The camera preserves source normals and
square ground on both axes. Read [projection.md](projection.md) for calibration.
The lit material helper uses geometric shadows rather than live AO: AO at native
scale can add dark pinholes that crawl across animated surfaces. Bake or paint
extra crease shading into stable UV maps when needed.

For an outlined whole modeled scene, set `object_outline: "23281d"` with
`outline: null` and native sampling. Put an integer `spriteforge_outline_id`
property on each asset's parent: 1–255 identify separate instances; 0 excludes
terrain and water. Descendants inherit that identity. The renderer writes a
visible identity AOV alongside each beauty frame; finishing adds one native
pixel inside each visible exterior silhouette. Enclosed foliage gaps stay open
without added dark rings. The identity pass's indexed colors label geometry;
they do not quantize the beauty image. Review occlusions and thin details.
Individual sprites use `outline` for a one-pixel exterior contour instead.

## Outputs

`scene.blend` retains the original editable scene and a `Pixel Render` scene with
static proxies for the first view/frame. Edit or animate the original scene and
rerun the pipeline; the proxy scene is not an animation rig.

`asset.json` contains effective settings, including the preview subset when
`--preview` is used. `raw/` retains Blender PNGs; `sprites/` has finished PNGs.
`atlas.png` puts frames in columns and directions in rows; `manifest.json`
records their rectangles, source hash, Blender version, scale, anchor, and checks.
`preview.png` shows the first frame; animation adds lossless `preview.webp`
and indexed compatibility `preview.gif`. Use WebP to judge color and cadence.
Tileable runs add a 3×3 `tiled-preview.png`.

## Deliberate limits

The pipeline samples the active source scene, viewport-visible geometry, and
assigned animations. Keep the selected asset visible in the active view layer.
Snapshot evaluation uses the viewport depsgraph; the exporter rejects different
viewport/render modifier switches or subdivision levels instead of silently
producing different geometry. Match them in an export copy of the source.
Assign an
action or NLA sequence before rendering separate clips. It does not invent
rigging, walk cycles, autotile masks, collision, or runtime integration. Root
motion is retained; author an in-place export action if travel leaves the cell.
Add root tracking only for a concrete asset that needs it, preserving vertical
movement and fixed pixel density.

Start with `assets/style.json`, then author readable forms and UV surface
fields. `lit_material` retains volume and material contrast with continuous
lighting. `pixel_material` emits paint for explicitly unlit art; `preserve` keeps
either graph. The renderer's normal-lit `bands` mode is a geometry study and
does not make a rounded tree or detailed model look hand-pixelled.
# Compose and record a scene

`scripts/compose.py` places exported atlases using their manifest anchors and
shared pixel density. Asset paths are relative to the scene JSON. Positions and
velocities are native pixels and pixels per second. Ground uses layer 0; objects
on layer 1 sort by their ground position. Integer `scale` enlarges recordings
without smoothing. Slower clips hold their own cadence in a faster scene;
the scene rejects a rate that would skip source poses.

```json
{
  "size": [320, 240], "fps": 12, "frames": 48, "scale": 2,
  "assets": {"traveler": "renders/walk"},
  "instances": [{"asset": "traveler", "direction": "east",
                 "position": [120, 180], "velocity": [21.3, 0]}]
}
```

```sh
uv run --script <skill>/scripts/compose.py --config scene.json --output scene-recording --mp4
```

This saves native frames, a still, a lossless animated WebP, a compatibility GIF,
and exact-rate MP4 (requires FFmpeg). Use `--no-gif` for WebP/PNG/MP4 delivery.
WebP retains full RGB colors and millisecond frame timing; GIF is indexed.
For a retargeted actor, multiply its action's `Travel speed` by the shared
`pixels_per_unit` to get scene pixels per second. Direct it along the selected
view: east +X, west −X, south +Y, north −Y. Review the moving recording for
foot sliding; adapted proportions or shoes can require contact refinement. `phase` offsets
an instance's animation by a number of frames. Optional `wrap_x: [-128, 448]`
wraps travel beyond the visible canvas; leave enough room to hide the complete
sprite at both ends.

For a closed patrol, supply `route: [[120,180],[220,180],[220,240],[120,240]]`
and `speed: 21.3` on the instance. The compositor follows those ground positions
at pixels per second, loops the route and selects the corresponding cardinal
facing. Use the actor's source-derived speed and include every facing it needs.
Routes can share the same continuous gait phase through turns.

Diagonal studio rendering preserves each object's authored camera, shadow,
diffuse, glossy, transmission and volume-scatter ray visibility. Camera-hidden
geometry can contribute shadows without appearing in the sprite or enlarging its
fitted canvas. These controls use Cycles; verify the chosen geometry and shadow
scale in the native animation.

In a Blender authoring script, `blender_scene.fit_canvas(scene, settings)` can
enlarge one fixed canvas to fit all configured frames/directions. It preserves
pixel density, pivot and anchor and restores the source frame. It does not
shrink the model or recenter individual poses.
