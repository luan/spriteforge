# Anatomical base

The body geometry and UVs in `humanoid.blend` are derived from Blender Studio's
**Human Base Meshes v1.4.1**, distributed under **CC0 1.0 Universal**.
The preparation script adds a deformation rig, weights, normalized scale, and
surface subdivision.

- [Official asset listing](https://www.blender.org/download/demo-files/)
- [Source bundle](https://mirror.blender.org/demo/asset-bundles/human-base-meshes/human-base-meshes-bundle-v1.4.1.zip)
- [CC0 terms](https://creativecommons.org/publicdomain/zero/1.0/)

The repository's `tools/vendor_humanoid.py` downloads the versioned bundle,
verifies its checksum, and rebuilds the portable base. No private source assets
or project files are needed.
