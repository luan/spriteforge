#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow>=12.1,<13"]
# ///
"""Verify face-material regions and packed UV paint through the Blender launcher."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="spriteforge render ") as temporary:
        directory = Path(temporary)
        for name, mid, dark in [("red", (170, 0, 0), (68, 0, 0)), ("blue", (0, 0, 170), (0, 0, 68))]:
            image = Image.new("RGBA", (16, 16), mid + (255,))
            for y in range(16):
                for x in range(8):
                    image.putpixel((x, y), dark + (255,))
            image.save(directory / f"{name}.png")
        subprocess.run(["blender", "--background", "--factory-startup", "--disable-autoexec",
                        "--python-exit-code", "1", "--python", str(ROOT / "tests/render_fixture.py"),
                        "--", str(directory)], check=True, capture_output=True)
        before = hashlib.sha256((directory / "source.blend").read_bytes()).hexdigest()
        # The saved source must work after its external image files disappear.
        for name in ("red", "blue"):
            (directory / f"{name}.png").unlink()
        settings = json.loads((directory / "settings.json").read_text())
        for shading in ("bands", "preserve"):
            if shading == 'preserve':
                settings.pop('shading', None)  # Default export must retain authored paint.
                settings.pop('palette', None)  # Textured export needs no color restriction.
            else:
                settings['shading'] = shading
            (directory / "settings.json").write_text(json.dumps(settings))
            output = directory / shading
            subprocess.run(["uv", "run", "--script", str(ROOT / "skills/spriteforge/scripts/pipeline.py"),
                            "render", "--source", str(directory / "source.blend"), "--config",
                            str(directory / "settings.json"), "--output", str(output)], check=True,
                           capture_output=True)
            with Image.open(output / "sprites/south-0001.png") as image:
                colors = set(image.get_flattened_data())
            reds = {p for p in colors if p[3] and p[0] and p[2] == 0}
            blues = {p for p in colors if p[3] and p[2] and p[0] == 0}
            if not reds or not blues:
                raise ValueError(f"{shading}: a face-material region was lost")
            if shading == "preserve" and (len(reds) < 2 or len(blues) < 2):
                raise ValueError("packed UV paint disappeared during export")
            if shading == "preserve":
                # Native sampling must retain sharp painted region boundaries,
                # including edges crossing between material regions.
                if reds != {(170,0,0,255),(68,0,0,255)} or blues != {(0,0,170,255),(0,0,68,255)}:
                    raise ValueError(f"native texture boundaries were blended or recolored: red={reds}, blue={blues}")
                if colors - reds - blues != {(0,0,0,0)}:
                    raise ValueError("native material boundaries were blended")
                with Image.open(output / "sprites/south-0001.png") as first, Image.open(output / "sprites/south-0002.png") as second:
                    if first.tobytes() == second.tobytes():
                        raise ValueError("UV animation disappeared during export")
        after = hashlib.sha256((directory / "source.blend").read_bytes()).hexdigest()
        if before != after:
            raise ValueError("source changed during export")
    print("Passed: face materials, packed UV texture detail and animation, source preservation, paths with spaces")


if __name__ == "__main__":
    main()
