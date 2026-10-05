#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Package only maintained files, excluding generated assets and local state."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "spriteforge"


def main() -> None:
    destination = ROOT / "dist"
    destination.mkdir(exist_ok=True)
    skill_files = [p for p in SKILL.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"]
    project_files = skill_files + [ROOT / "README.md", ROOT / ".gitignore", Path(__file__)] + list((ROOT / "tests").glob("*.py"))
    for name, files, base in [("spriteforge-skill.zip", skill_files, SKILL.parent),
                              ("spriteforge.zip", project_files, ROOT.parent)]:
        path = destination / name
        with ZipFile(path, "w", ZIP_DEFLATED) as archive:
            for source in sorted(files):
                archive.write(source, source.relative_to(base))
        print(path)


if __name__ == "__main__":
    main()
