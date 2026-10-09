# Source construction and material paint

## Build the design before the batch

A concept is a construction guide. Carry its body proportions, head and facial
features, costume layers, material changes, and major surface patterns into the
3D model. Render the model neutrally before applying the sprite projection;
the source should already be a coherent finished object. Low native resolution
makes a well-shaped model readable; it does not excuse missing anatomy or finish.

Run `pipeline.py review` on the authored source with its motion configuration.
It renders evaluated geometry under neutral studio lighting and the original
materials from four physical camera views at four motion phases. Examine the
clay views first: head/face placement, torso and limb proportions, clothing
volume, boot construction, strap fit, joint deformation and intersections.
Fix these in the authoring script. Then review UV paint around the whole model.
Keep the review beside the source; it must come from the same model used for
the native sprite exports. A camera-view picture or fitted silhouette is not a
substitute for this source review.

Use mesh density where it improves silhouette, joint deformation, facial planes,
cloth volume, leaf shape, and smooth normals. Match subdivision levels between
viewport and render. Bevel worked edges appropriately; keep planar surfaces
planar. Inspect wireframe and shaded views for pinching, intersections, lumpy
normals, oversized facets, and detached parts. Do not increase polygon counts
as a substitute for correcting the shape.

Size structural details in projected pixels. With density `p` and shear
`[sx,sy]`, a world-space difference `[dx,dy,dz]` projects to
`p * [dx + sx*dz, dy + sy*dz]`. At 24px/unit, a 0.014-unit board gap covers
only about a third of a pixel before directional compression. It cannot
reliably supply the reference's one-pixel board separation. Enlarge the actual
joint, change the construction count or simplify the design, and check another
facing. Use enough geometry for clean curves and deformation; choose staves,
folds and leaves by their visible size rather than adding many unresolved parts.

## Human foundation

`assets/humanoid.blend` contains a continuous anatomical body with UVs, fingers,
feet, a face, a hierarchical `Rig`, deformation weights, and matching surface
subdivision. It is a CC0 Blender Studio base prepared at 3.76 world units tall.
`assets/humanoid-license.md` contains its source and license. It needs costume,
hair, painted materials, and authored movement; it is not a finished character.

Open a copy or append `Body` and `Rig` with `bpy.data.libraries.load`. Keep their
skin weights and armature relationship. Adapt the anatomy to the concept.
Use continuous proportion changes across connected surfaces. An abrupt scale
change at a height cutoff can step the shoulders, collar or hood even when each
mesh has sufficient polygons. Apply the same anatomical transform to the body,
rig and fitted costume, and inspect the resulting surfaces before retargeting.
Derive fitted garments from a copy of the body surface, trim the appropriate
faces, offset along normals, and add cloth thickness and hems. Retain or transfer
body weights to those garments. Fit straps, cuffs, boots, pouches, and armor to
that surface rather than placing disconnected cylinders around it. Hide covered
skin faces where needed to prevent clipping. Build or fit hair to the skull;
the face and hands must remain recognizable at native scale.

Remove covered skin by anatomical region and deformation weights, then inspect
the exposed boundary. A single X/Z cutoff can leave toe or arm fragments beyond
the cutoff. Derive an ankle fit from anatomy, but construct a continuous boot
upper, toe box and sole; smoothing or enlarging individual bare toes leaves
their grooves in the footwear. Fit headgear around the evaluated skull and
review every facing for scalp intersections after changing its crown height.

A copied skin surface is only a garment foundation. Relax anatomical muscle
grooves beneath cloth, construct the garment's intended ease and drape, and add
folds at its actual tension points. Shape a boot's toe box and sole; remove the
individual bare-toe lobes from its outer surface. Match the source construction
to the concept rather than recoloring exposed anatomy as clothing.

Cut garment boundaries along clean interpolated edges or fitted pattern loops.
Deleting faces by their centers leaves stepped collars and cuffs that need
repair. Build hems from the actual boundary loops, and inspect the shoulder,
neckline, sleeve, waist, and boot transitions under deformation. Fit eyes inside
the orbital openings with surrounding lids; keep the exposed eye proportion
consistent with the face. Build a continuous hair mass with shaped directional
locks and a deliberate hairline. Review these forms in the neutral source and
the native sprite.

Keep a tunic and its free hem on a continuous surface, or give their joining
loops matching positions and weights. Fit a belt outside the evaluated garment,
including its thickness, rather than around the bare body's waist. Review these
joins through the clip: overlap in the rest pose can open under different weights.

The rig includes root, hips, spine, chest, neck, head, shoulder/upperarm/forearm/
hand, and thigh/shin/foot/toe bones with .L/.R sides. Preserve deformation and
add IK/control bones or gestures required by the motion; animate the control
structure rather than assigning disconnected rigid parts to fake limbs.

Before `bpy.ops.object.convert` or modifier application, deselect unrelated
objects and explicitly select and activate only the intended object. Operators
can apply modifiers to every selected object. Inspect the saved body and costume
armature modifiers, weights, and evaluated motion after these operations.

## UV paint and materials

Author portable PNG textures with meaningful material-specific clusters:

- Cloth: folds, seams, hems, panels, and controlled fabric variation.
- Leather/wood: seams, edge wear, grain following the construction, fittings.
- Skin/fur/shell: facial features, localized surface patterns and anatomical detail.
- Foliage: connected leaf groups, visible leaf orientation, occlusion, gaps.
- Stone: constructed joints or shaped fracture planes, grouped mineral variation.
- Ground/water: large connected forms, secondary clusters, readable boundaries.

Keep these features large enough to survive the native projection. A texture
filled with random pixels is not material painting. Use UVs tied to the authored
surface; keep density consistent and seams hidden or matched. Paint important
face/costume features in dedicated UV regions. Use clear directional wood or
cloth patterns; do not cover every object with the same generated noise.

Organize maps around surface construction: garment panels and seams, the
front/back of the head, boot uppers and soles, straps and fittings. Reusing one
striped image on every cloth or leather part does not describe those surfaces.
Paint each material's form, wear and accents where they belong, and inspect the
UV layout alongside front/back/side renders. Concept images remain design
references; the export uses this authored geometry and surface paint through
all poses and directions.

Map a field to the surface it describes. Wrap each trouser leg around its own
axis; a cylinder centered between both legs makes each leg sample a narrow
strip of the field. When one cloth field runs from hem to shoulder, assign
the skirt to its hem/waist section and the torso to its waist/shoulder section.
Reusing the entire field on both puts shoulder folds and hems in unrelated places.
Keep a cylindrical garment wrap seam behind the body, with its front centered
in the intended chart region. A mathematically valid unwrap can still place a
field's central chest folds on the back. Inspect its actual front/back assignment.
Bind a short free hem to the hips before transferring arbitrary leg weights;
leg deformation can split it into flapping panels. Transfer ankle weights into
a constructed boot shaft so it bends with the shin instead of leaving a separate
cuff floating above a rigid shoe.

For code-authored folds or cleavage planes, derive the UV marks from the same
surface coordinates used to construct the geometry. Keep the dark valley and
its adjacent highlight distinct: overlapping their falloffs can cancel both
and leave a plain fill. Compare the painted field on the unchanged mesh before
adding finer marks. A broad planar surface with one attached ridge can read
more clearly than many small triangles with independently changing normals.
Apply UV seam correction only to charts that actually wrap. A full-width planar
chart legitimately spans U=0 through U=1; treating that span as a cylinder seam
can collapse its paint onto one edge. Tube charts may wrap both axes and need
each seam handled separately.

Plan the projected coverage of focal marks. At about 64px human height, the
eyes must produce deliberate dark pixels, not subpixel pupils inside realistic
orbital geometry. Shape hair into a coherent mass with a few readable locks;
many tiny cylindrical strands become striped confetti. Check the actual face
from the sprite view before multiplying directions and animations.

Check the modeled feature width against pixel density. At 24 pixels per world
unit, a 0.02-unit pupil is less than half a pixel wide and can disappear under
native sampling. Adjust the modeled eye, iris and pupil together, then inspect
their coverage through the requested views and motion. Render smoothing cannot
make an undersized feature consistently readable.

For bitmap-assisted surface painting, supply the material's UV guide and its
chart conventions: front/back location, wrap seam, crown/root direction,
panel edges and projected pixel budget. Request surface fields rather than
images of a character or of complete objects. Keep the raw atlas and prompt.
Match texture density to the actual visible surface; cloth covering a few
dozen native pixels needs organized fold planes, not hundreds of tiny grain
marks. Check chart flips and strap/belt rotations against the authored UVs.
Keep guides and finished paint separate. When reusing baked paint, copy its
actual UV coordinates from the baked source and verify matching topology;
re-unwrapping an altered mesh can move its paint to different surfaces.

For a pixel-painted finish, ask for connected, stair-stepped material marks at
the chart's projected budget. Photographic fiber and smooth photographic folds
remain photographic when shrunk; a small PNG does not change their structure.
Keep nuanced RGB pigment and purposeful hue shifts, with finer accents attached
to folds, seams or wear regions. Inspect the actual field after generation.
Distinguish pigment/wear from authored form shading: `lit_material` lights
albedo; `pixel_material` retains painted shading. A studio camera works with
either shader. Avoid multiplying a complete painted lighting treatment by a
second full lighting pass.
For a shaded field that needs some modeled light and contact, use
`lit_material(..., paint_strength=.8)`: this preserves 80% authored paint and
20% physical shading. The blend retains texture alpha and full RGB. Choose it
by comparing the same model with albedo lighting and pure painted output;
it is not a universal material default. Ordinary albedo keeps `paint_strength=0`.

Measure UV paint against projected coverage, not PNG resolution. A 64-texel
shirt map may span only 16 native pixels vertically: a one-texel hem becomes a
quarter-pixel mark. Paint that hem several texels thick and check it through the
motion. Use broad form regions, connected secondary folds and a few focal
accents at a consistent detail scale. Large featureless fills with isolated
bright texels are an unfinished paint hierarchy, not useful extra detail.

Budget each chart separately. A 50px plant can contain leaves only 6–12px wide;
its shared leaf field needs veins sized for those leaves, not the whole plant.
Use an emitted UV gradient on a diagnostic copy to see each chart's projected
coverage. Filter its base pigment to that coverage, then author construction
marks at deliberate widths in the resulting field. For example, an 8×16 leaf
field can retain a one-texel connected vein that disappears in a 24×40 field
on the same small leaf. Keep full RGB pigment variation around those marks.
Likewise, a larger ground field needs a correspondingly larger world UV period:
128 texels over 128 native pixels adds detail; 128 over 64 pixels introduces
unresolved source detail. Do not give every material the same chart budget.

The renderer samples directly at native size by default, retaining full RGB
color and sharp painted boundaries. A palette is not required for textured exports. Leave
`cluster_materials` empty while authoring: automatic removal of small shades can
erase purposeful creases and material accents. Use it only for a tested cleanup
case and compare its result with the untouched paint.
Keep eyes, pins and other deliberate tiny accents in distinct unlisted palette
roles. Inspect native loops for remaining disappearing marks and strengthen
their paint or geometry; do not rely on cleanup to invent surface detail.

For textured lighting, add the skill's `scripts` directory to `sys.path`, then:

```python
from pathlib import Path
from materials import lit_material

cloth = lit_material("cloth", "637c4e", texture=Path("textures/cloth.png"), roughness=.9)
metal = lit_material("metal", "b0b9c0", roughness=.4, metallic=.75)
```

The helper packs textures and combines continuous shading, geometric shadows
and a small material-colored fill. Roughness and metallic response
distinguish surfaces. UV fields should describe construction and local material
variation rather than contain a second complete lighting pass. Skin and metal
need readable form and focal details; other main surfaces need authored maps.

Live ambient-occlusion nodes produce dark pinholes that crawl as native-sized
meshes move. Keep any extra crease occlusion in stable UV paint. Review adjacent
poses as well as held frames; a repeatable static render can still alias in motion.

Use `shading: preserve` and `lighting: studio` with the calibrated projection.
The default vertical shear is `[0,0.85]`; the diagonal Ravendawn study uses
`assets/ravendawn.json` and the camera described in [projection.md](projection.md).
Both studio cameras keep square ground tiles and shade undeformed geometry.
Review the actual native result: smooth shading is useful when it
explains the form, but it cannot repair missing costume or facial construction.
Filter unresolved texture grain once in the source map, then start with native
sampling. All material and exported colors remain unrestricted.

For explicitly unlit art, `pixel_material` emits packed UV paint directly.
The optional `scripts/bake_paint.py --form-guide` produces a reference-pose
lighting guide for repainting; it is not a finished texture. When applying such
maps to other clips, use `--reuse --uv-source` to retain their exact UV layout.
Do not rebake each animation pose or light an already shaded guide twice.
Keep original maps and concepts with the source.

Run `pipeline.py inspect` on the saved source to check UV layers, material names,
images, modifiers and topology. Inspect physical source views and native motion;
these structural facts alone do not establish visual quality.
