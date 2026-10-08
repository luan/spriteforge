# Asset construction and movement

## Characters and humanoid monsters

Start from the bundled anatomical base or a suitable licensed character mesh.
Adapt body proportions to the concept, preserve a continuous deforming surface,
and fit layered clothing. Finish the head, face, hands, fingers, feet, boots,
hair, and costume closures; their shapes must read in every view. A uniform
ellipsoid head on cylinder limbs is a blockout, not a finished humanoid.

Derive clothing from the body or transfer its weights to fitted garments.
Add collars, cuffs, seams, hems, belts, straps, closures, and appropriate folds;
keep those details consistent with the material and the pose. UV-paint skin,
cloth, leather, and equipment at a density that survives the native projection.
Compare the neutral model to the concept before shading or animation.

For movement, retarget a suitable bundled clip, then review actual foot contact,
knee/ankle articulation, weight shift, and secondary costume motion at the chosen sprite cadence.
See `animation.md`. Preserve the source clip's phase relationships; independently
oscillating limbs can pass closure checks while still looking unnatural.
Review face, hands, clothing intersections, and silhouette in all four directions.
Icons are separate assets; a baked costume does not imply equipment compositing.

## Creatures

Build the skeleton and major masses from the concept's anatomy. Construct
articulated limbs with coherent joint placement, shaped feet/claws, and a
recognizable face, mouthparts, or head. Smooth organic surfaces where appropriate;
use purposeful shell plates and creases rather than visibly overlapping spheres.
Model major details and UV-paint secondary surface structure. Keep patterned skin,
moss, fur, or chitin organized into connected regions that follow the surface.

Give the creature its own readable stepped gait and weight. Six-legged insects need stance
tripods, lifted swing legs, moving antennae, and a stable body. Slimes need
volume-aware squash/stretch, anticipation, recovery, and moving internal or
surface detail; uniformly scaling a sphere is only a motion blockout.

## Terrain

Author ground as UV-painted surfaces in Blender. Grass needs a connected
field with varied blade clusters and restrained bright tips. Judge its detail
density in a whole 64px tile beneath an actor; a mostly smooth field with a few
tiny marks is unfinished. Vary clump widths, heights, spacing and shade. Large repeated
turf islands read as separate decorative stamps rather than grass. Make several
interior variants, keep compatible borders and inspect a mixed patch beneath
actors. Soil needs connected compacted patches, shallow cracks and gravel groups that
read at native scale; broad sinusoidal variation alone looks like smooth clay.
Background contrast should support actor silhouettes. Ground is full-cell, opaque, one south view,
centered, and has no outer outline. Maintain shared pixel density with actors.

Make tile UV painting periodic across the border, including features that cross
edges. Match shoreline geometry to its painted bank. Keep water depth, submerged
features and shore colors fixed; animate a separate restrained ripple or caustic
layer. Moving the entire depth field makes the pond swim. Animate grass
with rooted phase-offset movement at 4–6 sprite poses per second. Both space and time must wrap.
Test neighboring variants together on every frame. Terrain transitions need
explicit masks for the requested neighbors and concave corners; show a composed
map that includes bends, intersections, shoreline, and mixed ground.

Use `tileable` for the exact border contract described in `workflow.md`. Some
continuous textures use different edge samples but still repeat visually; in
that case disable this conservative check and inspect animated repetition.

## Vegetation and decoration

Construct a tree from a tapered, branching trunk and shaped leaf groups with
real gaps, directional leaves, and visible branch relationships. UV-paint bark,
leaf clusters, and shadows. An icosphere pile with flat green materials is an
unfinished canopy. Avoid isolated dark dots and smooth featureless blobs. Match leaf width and
canopy density to their projected pixels; hundreds of thin overlapping blades
can create more noise than useful leaf structure.

Sway branches from their attachment points; leaves follow their branches with
restrained secondary motion. Keep trunk and roots planted. Flowers, reeds,
cloth decorations, and flame/light sources need appropriate held poses and timing.
Rocks and masonry need deliberate silhouettes, fracture or construction planes,
UV-authored surface clusters, and believable contact with the ground.

## Items and constructed props

Build the object's actual construction: sword bevels, point, guard, grip and
pommel; bottles with neck/rim, stopper and contents; chests with fitted boards,
hinged lid, metal bands, hardware and closure. Surface painting follows the
material: wood grain along boards, worn leather at edges, controlled metal
highlights. A box, cylinder, or three untextured cuboids is a blockout.

World props use shared density and placement pivots. Inventory presentations
may use centered composition and a separate scale. Animate meaningful states
with held poses—hinged openings, eased settle, flame, glint, or subtle loot hover—while
keeping construction and world scale consistent. Static walls/rocks remain
stable structural context in the animated scene unless movement is requested.
