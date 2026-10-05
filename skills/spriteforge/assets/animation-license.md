# Animation library

`animations.blend` contains the animation armature, 42 motions, and reference
T-pose from **Quaternius Universal Animation Library, Standard v3.0**. The creator
distributes the pack under **CC0 1.0 Universal**. The mannequin mesh is omitted.

- [Creator's pack page](https://quaternius.com/packs/universalanimationlibrary.html)
- [Official free download and license](https://quaternius.itch.io/universal-animation-library)
- [CC0 terms](https://creativecommons.org/publicdomain/zero/1.0/)

The included motions cover idle, walk, jog, sprint, crouch, jump phases, hits,
death, interaction, sword combat, spell casting, swimming, and other actions.
They retain the creator's 30 fps timing. Adapt the rig and contacts to the
character, and visually review the retargeted result.

To rebuild the bundled file, download the free `Universal Animation
Library[Standard].zip` from the official page, then run the repository's tool:

```sh
uv run --script tools/vendor_animations.py '/path/to/Universal Animation Library[Standard].zip'
```

The verified archive SHA-256 is
`cc73fc4e495b82958207316596317a3f40b9fa38065bde1027937452da537724`.
The tool extracts the in-place `Unreal-Godot/UAL1_Standard.glb` and its `_RM`
root-motion variant. It retains the in-place clips and records each clip's
original travel speed from the root-motion data, then saves the motion-only
Blender library. Installed skills already contain it and require no download,
account, paid source pack, or animation add-on.
