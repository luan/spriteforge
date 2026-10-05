#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Rebuild the bundled anatomical base from Blender Studio's CC0 asset bundle."""
import hashlib
from pathlib import Path
import subprocess
import tempfile
from urllib.request import Request, urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
URL = "https://mirror.blender.org/demo/asset-bundles/human-base-meshes/human-base-meshes-bundle-v1.4.1.zip"
SHA256 = "811f43accbb31a88266d932f8f5563b2d13586fca0ba2693aad1f5fe582b3515"


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="spriteforge-base-") as temporary:
        directory = Path(temporary)
        archive = directory / "source.zip"
        with urlopen(Request(URL, headers={"User-Agent": "Spriteforge/1.0"}), timeout=60) as response:
            archive.write_bytes(response.read())
        if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
            raise ValueError("asset bundle checksum changed")
        source = directory / "source.blend"
        with ZipFile(archive) as bundle:
            source.write_bytes(bundle.read("human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend"))
        subprocess.run(["blender", "--background", "--factory-startup", "--disable-autoexec",
                        "--python-exit-code", "1", "--python", str(ROOT / "tools/prepare_humanoid.py"),
                        "--", "--source", str(source), "--output",
                        str(ROOT / "skills/spriteforge/assets/humanoid.blend")], check=True)


if __name__ == "__main__":
    main()
