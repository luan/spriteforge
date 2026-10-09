# Calibrating an oblique game view

For a Ravendawn-style view, start from `assets/ravendawn.json`. Its diagonal
projection is a calibration starting point; it does not establish finished art
quality. Compare the actual requested reference and occupied asset size before
authoring the rest of a set.

The renderer projects an undeformed source point to:

```text
screen X = world X + shear X * world Z
screen Y upward = world Y + shear Y * world Z
```

Ground tiles keep their original X/Y size. A raised object with
`shear: [-0.45, 1.1]` shifts left and upward while retaining cardinal ground axes.
The horizontal and vertical height offsets are independent; assuming equal
offsets can make a standing character appear excessively diagonal.
Measure the displacement between
corresponding top/base features on walls, posts or simple props to calibrate
the height projection. Keep object height and width as separate model parameters.
Check a second asset before accepting the camera.

For seams intended to read as connected lines, measure width perpendicular to
the projected edge. A gap one pixel wide along world X can be narrower across
a diagonal edge. Project world vectors `e` along the edge and `w` across its
actual gap with the equations above, after applying the facing and pose:

```text
gap pixels = pixels per unit * abs(e.X * w.Y - e.Y * w.X) / length(e)
```

Here `e` and `w` are the projected 2D vectors. Review another pose if the edge
projects to zero length. When a seam breaks into dots, enlarge its projected
width or paint a connected joint in UV space. Back modeled gaps with recessed
geometry when they should remain opaque. Match surface-map density to projected
coverage as well; narrow framing needs fewer texels across it than broad panels.

With `lighting: studio` and a nonzero horizontal shear, the renderer uses a
Cycles OSL camera to cast these rays directly. It retains source geometry,
normals, UVs and material coordinates instead of shearing geometry for shading
or warping a finished sprite. The saved render scene includes the camera source
and compiled shader. Official Blender builds with OSL support are required.
CPU rendering is selected for portability; custom cameras cannot use Metal/HIP.
Cycles uses its own `filter_width`, separate from the general render filter.
The renderer sets it to 0.01px and retains 128 lighting samples. Leaving its
default 1.5px filter active blends native texture marks and neighboring geometry;
changing the PNG size or general render filter alone does not correct that.
See [Blender's custom camera documentation](https://docs.blender.org/manual/en/latest/render/cycles/osl/camera.html).

Vertical-only studio views keep the existing EEVEE camera. Key mode remains a
geometry-sheared rendering mode for explicit painted or banded studies.

Use the same projection and pixel density for every asset in a scene. Review
cardinal views with the model's true world orientation; an arbitrary per-asset
yaw can conceal a camera error in one view while making the others inconsistent.

Compare original assets against the reference's quality in three areas: readable
modeled forms, surface construction/detail, and lighting/color. Shape the asset
from its own design; matching a particular reference silhouette is relevant only
when that asset was requested. Keep the actual source/clay review and an unseen
facing or motion pose beside each accepted render.
