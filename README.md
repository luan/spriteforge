# Spriteforge

Blender tooling for textured, animated RPG sprites: native PNGs, directional
atlases, animation manifests and scenes composed from independent sprites.
The art workflow is still under development.

```sh
npx skills add luan/spriteforge
```

Ask an agent to use `$spriteforge` with a description or concept, native asset
size, directions and animations. Requires `uv` and Blender 5.2+; FFmpeg is
optional for MP4 recordings.

The package includes rendering, UV material helpers, motion retargeting,
per-entity sheet painting and sprite composition. Editable Blender sources and
reproducible authoring inputs belong with every delivered asset. RGB colors are
unrestricted; animation cadence is configurable.

[Skill workflow](skills/spriteforge/SKILL.md)
· [Render settings](skills/spriteforge/references/workflow.md)
· [Animation library and attribution](skills/spriteforge/references/animation.md)
