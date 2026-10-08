# Tile-based RPG sprite delivery

Use the shared rendering style from `style.md`; inspect the target catalog
before choosing asset IDs. Export PNGs plus KDL fragments ready to merge into
the existing files without renumbering or replacing unrelated sprites.

## Scale and placement

Compatibility cells are 64×64 ground/items, 128×128 characters and larger props,
and 128×64, 64×128, or 128×128 walls. Trees may need a 256×256 cell. Preserve
the preset's pixel density across world assets. At that density a 64px ground
tile is `64 / pixels_per_unit` world units wide, about 2.667 at 24px/unit.

The renderer anchors cells at their bottom-right against the map tile. Place
the world pivot at the center of the final 64×64 region: anchor [0.5,0.5] for
64px cells, [0.75,0.75] for 128px, [0.875,0.875] for 256px. For a rectangular
cell use [1-32/width,1-32/height]. Keep character feet at this pivot. Inventory
icons may be centered separately. Sprite displacement is in legacy 32px units,
so displacement=8 shifts a compatibility sprite 16px up-left; do not combine
that shift with an already-correct anchor accidentally.

Ground: one south view, centered anchor, outline null, full opacity. For
periodic ground, make authored clusters wrap across opposite boundaries and
enable `tileable`. Water and wind loops need genuinely changing pixels and a
closed motion cycle. Transition masks and wall corners must be authored for
the requested neighboring materials; a repeating tile alone is insufficient.

## Catalog fragments

Atlas geometry belongs in `assets/sprites.kdl`. Always write atlas-w/atlas-h
explicitly for sheets smaller or larger than the default 1024px. Animation
frames occupy contiguous cells. The Spriteforge atlas has frames in columns
and directions in rows.

```kdl
atlas "new-guard" file="new-guard.png" cell-w=128 cell-h=128 atlas-w=3072 atlas-h=512
sprite "new-chest" atlas="new-chest" cell=0
sprite "new-water" atlas="new-water" cell=0 frames=12 {
    animation frames=12 duration=83
}
```

Atlas editor metadata belongs in `assets/sprites/project_spritesheets.kdl`:

```kdl
sheet "new-guard.png" sprite-type="character" cell-w=128 cell-h=128 cols=24 rows=4
```

Use sprite-type ground, object, character, effect, or wall. Add a populated
child with occupied row-major cell indices for partially filled sheets.

Character poses belong in `assets/outfits.kdl`; reference the actual row for
each direction rather than assuming older sheets use the same order:

```kdl
outfit "new-guard" {
    pose kind="idle" dir="east" atlas="new-guard" row=0 col=0
    pose kind="walk" dir="east" atlas="new-guard" row=0 col=0 frames=24
    pose kind="idle" dir="north" atlas="new-guard" row=1 col=0
    pose kind="walk" dir="north" atlas="new-guard" row=1 col=0 frames=24
    pose kind="idle" dir="west" atlas="new-guard" row=2 col=0
    pose kind="walk" dir="west" atlas="new-guard" row=2 col=0 frames=24
    pose kind="idle" dir="south" atlas="new-guard" row=3 col=0
    pose kind="walk" dir="south" atlas="new-guard" row=3 col=0 frames=24
}
```

Gameplay templates, collision, creature stats, and equipment composition are
separate from image generation. Include them when requested. Finish sprite
delivery by checking a composed scene for shared scale, pivots, overlap,
directional readability, terrain joins, and animation; catalog syntax alone
does not verify their appearance in the game.
