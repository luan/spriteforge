# Held pixel animation

Start with 12 sprite poses per second for locomotion and 4–6 for idle,
vegetation and water. Choose the cadence from the desired pixel-art language;
preserve an explicit request. Quality comes from readable poses, contacts,
weight and timing. Dense motion capture can guide those poses without becoming
30 independently rendered sprite frames per second.

Keep source time and sprite cadence distinct. The bundled walk contains 40
source samples at 30fps, lasting 1.333 seconds. Retargeting it at 12fps produces
16 poses with the same duration. For a finished 30fps source, export source
frames `1 + round(i * 40 / 16)` for `i = 0..15`, with asset `fps: 12`.
Changing the playback rate of all 40 frames to 12 would slow the walk to 3.333
seconds. The renderer's frame list selects source states; its `fps` sets their
playback cadence. Source frames may therefore have intentional gaps.

Hold each chosen sprite until its next pose. Engine or video frame rates may
be higher, but neither interpolation nor additional rendered in-between poses
should erase that cadence. Scene composition holds slower clips at their own
rate. Idle/environment movement should remain restrained rather than keeping
every object constantly rotating or bobbing.

## Actors

Prefer the bundled Quaternius CC0 library for human motion. It contains 42
motions and a reference T-pose, including `Idle_Loop`, `Walk_Loop`,
`Walk_Formal_Loop`, `Jog_Fwd_Loop`, `Sprint_Loop`, `Sword_Idle`, `Sword_Attack`,
`Interact`, `PickUp_Table`, `Jump_Start`, `Jump_Loop`, and `Jump_Land`.
See [the source and license](../assets/animation-license.md). No account,
paid animation pack, or external add-on is needed for the installed library.

After adapting the anatomy, fitting the costume, and completing skin weights:

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 1 \
  --python <skill>/scripts/retarget.py -- \
  --source character.blend --output character-walk.blend --action Walk_Loop
```

The default target armature is `Rig`, with the names in `assets/humanoid.blend`.
Apply armature rotation/scale and face -Y. Use `--rig NAME` and
`--bone-map mapping.json` for another humanoid: JSON maps target bone names
to library bone names and must include a hip mapped to `pelvis`. The retargeter
calibrates bone direction and roll between the source T-pose and target rest
pose. It bakes quaternion keys at `--fps 12`, preserves the input, and saves
to a fresh file. This is a starting motion transfer, not automatic final polish.

Read the resulting scene frame range for export. Indivisible durations round to
the nearest pose interval; one-shot actions retain the exact source endpoint.
For loops, the first pose repeats one frame after the export range, correcting
small discrepancies in imported closing keys. This closing pose is
excluded from the sprites. One-shot actions include their final pose. The action
stores `Source clip`, `Motion source`, `Export frames`, `Loop`, `fps`, and
`Travel speed` in world units per second, scaled from the creator's root-motion
variant. Multiply travel speed by pixel density when composing a moving scene.
Generate each clip from the same authored character, or keep completed actions
in one source and explicitly activate the desired action before rendering.

Review the whole retargeted motion on the dressed character. Adapted proportions
can change foot placement, hand reach, costume clearance, and stride. Refine
stance contact with IK or constrained targets when needed, then bake the fix.
Keep a shared floor reference and fixed pivot across clips; never recenter each
frame or clamp every foot to the floor. Preserve jump height, body weight shift,
toe roll, and source timing. Keep hands out of the hips and legs out of long hems.
Review velocity at the loop seam and blend transitions when sequencing actions.
Do not replace a reviewed source gait with independent guessed limb oscillations.

Use a deformation rig and fitted weighted costume. Author contact, down, passing,
and up phases with grounded stance feet, lifted swing feet, toe roll, knee bend,
hip weight transfer, counter-rotating shoulders, and opposing arms. Use IK foot
targets or equivalent planted-foot solving. Feet move backward during in-place
stance by the implied ground speed; combine this with the same speed when moving
the character in a scene. Do not slide a planted foot across the ground.

Give creatures a gait suited to their anatomy: alternating tripod contact for
six-legged insects, body weight and paw contact for quadrupeds, and volume-aware
squash with anticipation/recovery for soft creatures. Clothing, antennae, packs,
and foliage need restrained secondary motion. Parent them to a coherent rig;
independent rotating cylinders are not a character deformation system.

## Environment and objects

Water motion must travel coherently and wrap in space and time. Animate grass and
branches from their rooted bases with phase-offset sway; attached leaves follow
their branch. Preserve the trunk's ground contact. For chest/door states, pivot
at the real hinge and include easing and settle. For a loot presentation, animate
subtle hover/rotation or a deliberate glint without changing world scale. Keep
static structure stable while animating its appropriate moving part.

## Export and review

Keep the pivot and anchor fixed. For in-place actions remove horizontal root
travel while retaining vertical movement. Normalize consecutive quaternion signs
and prevent overshoot on baked keys. To make a loop, author a closing pose at the
next frame after the export range that matches the first pose and velocity;
export the cycle without duplicating the endpoint as a pause.

Inspect the full source animation and native sprite recording at their own rates. Check
joint deformation, intersections, foot contacts, cyclic position and velocity,
texture swimming, flicker, silhouette changes, and clipping at motion extrema.
Render contact sheets for the key phases and verify the exported PNGs actually
change through the motion. A deliberate hold can repeat; a duplicate-only loop
cannot claim motion. Ground seams must agree on every frame.

Prefer lossless animated WebP for full-RGB scene review. It retains the native
paint colors and uses millisecond frame durations. GIF durations have 10 ms granularity. The renderer alternates durations to keep
the requested average rate. Include an MP4 recording at the chosen sprite rate,
using FFmpeg when available, and retain native PNG frames and timing
metadata so the source can be exported without that optional recording tool.
