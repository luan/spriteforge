---
name: spriteforge
description: Author textured RPG characters, monsters, terrain, props, and items in Blender and export directional pixel sprites with editable sources and stepped animation.
---

Build actual textured, rigged 3D assets and render them onto a native pixel grid.
Prioritize readable anatomy, rich material detail, volume and consistent motion.
A modest 3D appearance is appropriate when it improves those qualities. Establish
one treatment for the whole asset set. Color count is unrestricted.
Use reference games to benchmark the quality of original assets and scenes:
readable forms, rich material detail, deliberate pixel structure and stable
animation. Reconstruct particular characters or scene layouts only when asked.

Resolve resources relative to this skill. Run host Python through `uv run
--script`; run `bpy` scripts inside Blender. Read
[art-direction.md](references/art-direction.md) for size and visual references,
[authoring.md](references/authoring.md) for construction and surface maps, and
the relevant section of [categories.md](references/categories.md).
[workflow.md](references/workflow.md) documents the renderer and output contract.
For a Ravendawn-inspired presentation, use
[projection.md](references/projection.md) and `assets/ravendawn.json` to calibrate
the diagonal view before modeling a batch.
An optional [whole-sheet painting route](references/sheet-painting.md) prepares
one entity's modeled poses for imagegen editing. It requires visual review of
silhouettes, interior placement and temporal consistency before delivery.
Export each entity independently, including reusable terrain tiles and water
frames. Assemble the final scene with `scripts/compose.py`, retaining independent
placement, facing, animation and depth ordering.

1. Establish tile size, occupied asset size, canvas and animation cadence.
   Unless specified otherwise, use 64px ground tiles, a roughly 64px human,
   24 pixels per unit, 12fps locomotion and 6fps idle/environment. Transparent
   padding does not add detail. Adapt the design's proportions and important
   features to their actual projected pixels before producing a batch.
2. Build a finished editable model. Humans can start from the bundled CC0
   `assets/humanoid.blend`; fit costume surfaces and transfer skin weights.
   Model anatomy, facial features, garment layers, folds, joints and object
   construction. Retain the rig. Review physical clay and material views with
   `scripts/pipeline.py review`, including motion extrema in every facing.
   Repair intersections, pinching, deformations and weak silhouettes here.
3. Author UV surface fields tied to construction: seams, folds, edge wear,
   wood grain, leaf structure, skin patterns and hardware. Use
   `scripts/materials.py:lit_material` for packed textures, continuous shading,
   geometric shadows and material-specific roughness/metallic response.
   Keep the projection calibrated in step 1. Default render settings in
   `assets/style.json` use `shading: preserve`,
   `lighting: studio`, `shear: [0,0.85]`. The physical camera preserves square
   ground tiles without deforming the model for lighting. For explicitly
   painted/unlit art, `pixel_material` and `lighting: key` remain available.
   Concept art can guide the design; do not project a finished character image
   onto a fitted model as a substitute for modeling and surface authoring.
4. Render a small native sample before multiplying views or poses. Main features
   should read in connected areas; tiny source texels should not sparkle through
   broad fills. Match surface-map density to the occupied sprite and filter
   unresolved texture detail in the material input. Start with `supersample: 1`;
   compare optional coverage averaging at native size before adopting it.
   Improve source detail and material contrast when an asset looks flat or muddy.
   Reducing the palette or imposing shade bands does not establish pixel art.
   Use the reference's exterior contour treatment. Whole modeled scenes can use
   the visible asset identity pass in `workflow.md`. Keep enclosed leaf gaps free
   of extra dark rings. Inspect light and dark backgrounds and adjacent poses.
5. Use reviewed motion sources for humans. The bundled CC0 library covers idle,
   locomotion, combat and interaction; `scripts/retarget.py` retains source timing
   and attribution. Inspect contacts, foot speed, weight shifts, grips and loop
   transitions after retargeting. Author appropriate deformation or state changes
   for other assets. Keep one pivot, pixel density and anchor across the clip.
   Read [animation.md](references/animation.md) for playback and validation.
6. Export complete clips into fresh directories. Inspect four directions and a
   complete held-pose loop at native and integer enlarged scale. Use full-RGB
   PNGs and lossless WebP for review; GIF is an indexed compatibility format.
   Export each entity and clip independently, with a manifest and atlas. Compose
   these assets at the same ground scale and retain each clip's authored cadence.
   Record the composition, including animated characters, monsters and water,
   reusable terrain, props, items and decoration. Inspect overlap and anchors.
7. Deliver native PNGs, atlases, manifests, recordings, packed textured `.blend`
   sources, maps, design inputs and reproducible authoring scripts. Rebuilding
   must start from those inputs, rather than rerendering an unexplained finished
   model. Report export checks separately from visual findings. A successful
   render or polygon count cannot establish production art quality.

Use `bands` only for intentional geometry/color studies; it replaces source
materials. Keep `cluster_materials` empty unless a before/after comparison shows
that selective cleanup helps. For KDL RPG catalogs, read
[rpg-catalog.md](references/rpg-catalog.md). Preserve original files and rigs.
