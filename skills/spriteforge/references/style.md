# Oblique RPG pixel style

Read `art-direction.md` and establish the requested native size first. Start
asset settings from `assets/style.json`. Its material color ramps are authoring
swatches, not an export limit. Choose colors
for the painted form and material features: occlusion, shadow, base and accents.
Keep material identity in the shadows and highlights. The export preserves
the source's RGB colors without a count cap. Shape, surface painting, and
deliberate detail at native resolution establish the pixel-art treatment.

## Projection and shading

- The shared projection keeps X unchanged and uses Y += 0.85 Z.
  With `lighting: studio`, a physical orthographic camera and aspect correction
  retain square ground tiles while lighting the original geometry. Use this
  projection for the whole set. Studio lighting supports vertical shear only.
  The legacy `lighting: key` proxy renderer also supports diagonal shear.
- East 90°, North 180°, West 270°, South 0°. Author the south-facing model
  toward -Y. Maintain the same scale through directions and animation.
- Use UV surface fields and continuous material lighting for volume, contact
  shadows and material contrast. Keep cloth matte, leather restrained, and metal
  highlights broad enough to read. Moderate 3D shading is acceptable. For an
  explicitly unlit treatment, emit authored paint with `pixel_material`.
- EEVEE, Standard view, transparent RGBA. Studio lighting accumulates 32 samples
  on the native grid with a narrow reconstruction filter; legacy key mode uses one.
  Render at the target size without averaging painted boundaries.
  Leave `cluster_materials` empty while authoring;
  automatic removal of small shades can erase useful painted detail.
  Threshold alpha at 128, preserve RGB colors, add a one-pixel #23281d
  exterior contour for the outlined RPG treatment, and enlarge only with nearest-neighbor integer
  scaling. The preset enables exterior contours. Whole modeled scenes use the visible
  asset identity pass described in `workflow.md`. Review thin parts and use painted selective edges when a uniform contour obscures them.

The starter preset uses 24 pixels per world unit. The bundled anatomical base is
3.76 units tall; a 64px ground tile spans about 2.667 units. Calibrate the shared
density against the requested visible size and the first native render.
Extra canvas accommodates large props and motion without shrinking them.
Inventory icons may use a separate presentation scale.

## Author the asset

From a description, model the anatomy, silhouette, costume, and material regions
in Blender, then save the editable source. Reuse a suitable model and rig when
available. The bundled `create_demo.py` is a renderer fixture, not an art template.

From concept art, preserve its design in all requested views. Keep the concept
and native sprites together so the interpretation is visible. If concept art
is part of the request, generate it with the available image tool, then continue
through modeling and sprite export. A concept image alone is not sprite delivery.

Judge features in the native render: faces, grips, leaf groups, and clothing
edges need connected pixel clusters. Use enough geometry and paint to support
the requested size and deformation.
Use separate material regions or UV-authored clusters for important details.
Use gloss where it communicates a material. Avoid unresolved grain and bright
isolated marks; match the material field to the projected native detail.
Read `categories.md` for the requested asset before authoring it.

Judge volume and pixel structure separately. Overlapping forms need readable
occlusion, material-specific shadows, and highlights that explain their shape.
Pixel structure needs connected painted regions with deliberate boundaries and
small accents placed where they communicate a feature. Smooth gradients with
generic stripes remain a texture study, even when sampled onto a pixel grid.

Choose scene colors from comparable biomes in the references. Daytime woodland
needs distinct green vegetation, warm earth and wood, and blue water; averaging
unrelated cave, desert and forest colors produces a dull olive cast. Review the
whole native scene for material separation. Tune authored surface colors rather
than applying a final image grade that individual exports cannot reproduce.

## Animation

Keep the deformation rig and source actions. For walking, use planted-foot
stance targets, alternating swing, modest hip bob, and opposing arm motion.
Keep horizontal root travel out of an in-place export action while retaining
jump height. Preserve quaternion signs between adjacent keys; use linear
interpolation for dense baked samples. A hand gesture must read in the sprite.

Use one fixed pivot, anchor, and pixel density through the clip. Check motion
extrema before export, enlarge the cell if needed, and inspect a complete loop
for sliding feet, disappearing features, and pixel swimming. Never recenter
individual frames to conceal cropping. The renderer samples authored animation;
the agent must create the requested movement when it does not exist.
