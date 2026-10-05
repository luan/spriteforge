---
name: spriteforge
description: Render editable Blender models into directional RPG sprites and animation atlases.
---

Resolve resources relative to this skill. Run host Python through `uv run
--script`; scripts importing `bpy` run inside Blender.

Inspect the source with `scripts/pipeline.py inspect`. Establish native sprite
size, pixel density, directions, frames and a fixed anchor in the asset JSON.
Render a small sample with `scripts/pipeline.py render --preview` before exporting
the full clip into a fresh directory. Preserve the source model and rig.
Review all requested facings and animation poses at native and integer zoom.
Export PNG sprites, atlas, manifest and previews with the editable source.
Technical validation does not establish visual quality.
