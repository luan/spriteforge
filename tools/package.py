#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Package the committed skill and project without including local experiments."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    destination = ROOT / "dist"
    destination.mkdir(exist_ok=True)
    for name, tree in [("spriteforge-skill.zip", "HEAD:skills/spriteforge"),
                       ("spriteforge.zip", "HEAD")]:
        path = destination / name
        subprocess.run(["git", "archive", "--format=zip", "--prefix=spriteforge/",
                        "--output=" + str(path), tree], cwd=ROOT, check=True)
        print(path)


if __name__ == "__main__":
    main()
