#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Rebuild the bundled motion library from Quaternius's free Standard archive."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SHA256 = "cc73fc4e495b82958207316596317a3f40b9fa38065bde1027937452da537724"
MEMBER = "Universal Animation Library[Standard]/Unreal-Godot/UAL1_Standard.glb"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="free Standard zip from the official itch.io page")
    parser.add_argument("--blender", default="blender")
    args = parser.parse_args()
    if hashlib.sha256(args.archive.read_bytes()).hexdigest() != SHA256:
        raise ValueError("animation archive checksum differs from the bundled version")
    with tempfile.TemporaryDirectory(prefix="spriteforge-motion-") as temporary:
        source = Path(temporary) / "library.glb"
        root_motion = Path(temporary) / "root-motion.glb"
        with ZipFile(args.archive) as archive:
            source.write_bytes(archive.read(MEMBER))
            root_motion.write_bytes(archive.read(MEMBER.replace(".glb", "_RM.glb")))
        subprocess.run([args.blender, "--background", "--factory-startup", "--disable-autoexec",
            "--python-exit-code", "1", "--python", str(ROOT / "tools/prepare_animations.py"),
            "--", "--source", str(source), "--root-motion", str(root_motion), "--output",
            str(ROOT / "skills/spriteforge/assets/animations.blend")], check=True)


if __name__ == "__main__":
    main()
