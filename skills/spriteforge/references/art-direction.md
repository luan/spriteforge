# Visual references and native detail

Use these six references with equal weight:

- [Phobos Online](https://www.phobosonline.com/)
- [Zezenia Online](https://www.zezeniaonline.com/)
- [Tibia](https://www.tibia.com/mmorpg/free-multiplayer-online-role-playing-game.php)
- [Bloodstone](https://www.bloodstoneonline.com/en/)
- [Ravendawn press kit](https://ravendawn.online/en/press-kit) and [game screenshots](https://ravendawn.online/en/media)
- [Medivia Online](https://medivia.online/mmo)

Study their in-game characters, terrain, vegetation, equipment, and buildings.
Use them to guide original designs. Their shared visual language is oblique
fantasy pixel art with readable silhouettes, modeled volume, rich painted
material detail, and controlled contrast. They contain different palettes and
levels of detail; choose a coherent treatment for the requested asset set.

## Size comes first

Record the native visible size, tile size, canvas size, and animation rate before
authoring. A 128px canvas containing a 48px character has a 48px detail budget.
Transparent padding and an enlarged preview do not add detail. If no size is
specified, use 64px ground tiles and target a character around 64px tall inside
a 128px canvas, with 12fps locomotion and slower idle motion. This uses 64×64 ground tiles, twice the
32px tile convention, while retaining the character-to-tile proportions of
the reference games. Establish pixel density once for the asset
set, then model every world asset at that density. A larger tree needs more
canvas; it should retain its scale relative to the character.

Measure the first native render's occupied bounds. Adapt the model's proportions,
face, costume, surface paint, and geometry to that budget before generating the
full set. Use a gameplay idle pose for this prototype and sample walk extrema
in every facing before the full animation batch. Keep the camera, density,
pivot, and anchor fixed across the animation.
When a requested size changes, re-author the details and re-render at that size.

| Visible size | Detail to author |
| --- | --- |
| About 24–32px | Strong silhouette, deliberate face/weapon marks, a few broad folds, distinct major material regions. |
| About 48–64px | Clear face and hair shape, layered collar/cuffs, readable fastenings, grouped folds and wear, shaped leaf clusters. |
| About 96–128px or larger | Finer facial planes, construction seams, fitted hardware, patterned textiles, structured surface wear, richer leaf/stone forms. |

These are design budgets, not automatic quality thresholds. A buckle may need
several pixels at one size and one deliberate highlight at another. Projected
texel size matters: use larger surface features where the view compresses them.

## Shape and painted finish

Give characters enough head and hand area for their role to read. Preserve
credible joints and limb structure while adapting proportions to the native
projection. For a 64px human, start with a visible head about 12–16px tall,
then compare the rendered proportions against gameplay artwork. A realistic
base often needs a larger head and hands, a broader costume silhouette, and
shorter legs to reach this treatment. Change the source anatomy and weights;
scaling the complete sprite does not fix its proportions. Keep the
face visible beneath hair and headgear; clothing should communicate its layers,
fit, closures, folds, and material. Enlarge a meaningful feature or move it into
a readable plane when it disappears at the target size.

Inspect how the overhead view hides facial planes. Adapt the hairline and face
presentation for this view; a modest upward head/face angle can expose the eyes
without enlarging them into protruding spheres. Apply a shared presentation
offset consistently through the source clips, preserve their relative motion,
and inspect the neck, silhouette, and all facings again.

Author seams, wear, and surface patterns in connected areas that describe the
object. Continuous material lighting can supply form, contact shadows and
highlights; reserve emitted paint for an explicitly unlit treatment.
Use crease/contact shadows to separate costume layers and overlapping forms;
bake ambient occlusion or paint it into the surface maps where useful. Wood
grain follows boards, folds follow tension, foliage has overlapping leaf shapes,
and stone has shaped fracture planes. Keep important highlights brighter than
background detail. Add finer clusters when the requested native size supports
them; avoid both featureless broad bands and uniform procedural speckle.

Use selective dark edges and internal occlusion to clarify forms. An optional
one-pixel outer contour can help at small sizes, but a uniform dark border must
not swallow fingers, leaf gaps, or facial features. Test the sprite on light and
dark ground at native scale. Reserve the darkest clusters for occlusion and the
brightest for focal accents.
Choose the palette from the actual painted features and native render. Add shades
when they carry useful form or material information; a fixed per-material color
count cannot establish this style. Uniform bands across rounded surfaces read
as a toon render.

Review the actual sprite beside reference gameplay artwork at comparable
visible size. Judge silhouette, face, material separation, surface richness,
lighting, and animation together. A detailed neutral model can still produce
a weak sprite; fix the authored shape or paint that caused the weak result.
