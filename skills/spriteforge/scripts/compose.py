#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow>=12.1,<13"]
# ///
"""Compose exported sprites at their native scale and record their actual motion."""
import argparse
import json
import math
from pathlib import Path
import subprocess


def route_position(points, speed, time):
    if len(points) < 2 or not math.isfinite(speed) or speed <= 0:
        raise ValueError('route requires at least two points and a positive finite speed')
    segments = []
    for start, end in zip(points, points[1:] + points[:1]):
        dx, dy = end[0] - start[0], end[1] - start[1]
        distance = math.hypot(dx, dy)
        if not math.isfinite(distance):
            raise ValueError('route coordinates must be finite')
        if distance:
            segments.append((start, dx, dy, distance))
    length = sum(part[3] for part in segments)
    if not length:
        raise ValueError('route must travel between distinct points')
    travel = (time * speed) % length
    for start, dx, dy, distance in segments:
        if travel < distance:
            direction = ('east' if dx > 0 else 'west') if abs(dx) > abs(dy) else ('south' if dy > 0 else 'north')
            return start[0] + dx * travel / distance, start[1] + dy * travel / distance, direction
        travel -= distance
    raise ValueError('route position is outside its total distance')


def record(config_path: Path, output: Path, mp4: bool, gif: bool = True) -> None:
    from PIL import Image
    config = json.loads(config_path.read_text())
    width, height = config["size"]
    fps = config.get("fps", 12)
    count = config["frames"]
    scale = config.get("scale", 1)
    if min(width, height, fps, count, scale) <= 0 or not isinstance(scale, int):
        raise ValueError("size, fps, frames, and integer scale must be positive")
    assets = {}
    for name, relative in config["assets"].items():
        directory = config_path.parent / relative
        manifest = json.loads((directory / "manifest.json").read_text())
        if len(manifest["frames"]) > 1 and manifest["fps"] > fps:
            raise ValueError(f"{name}: scene rate would skip animation poses")
        assets[name] = (manifest, Image.open(directory / manifest["atlas"]).convert("RGBA"))
    densities = {manifest["pixels_per_unit"] for manifest, _ in assets.values()}
    if len(densities) != 1:
        raise ValueError("scene assets must share one pixel density")
    instances = config["instances"]
    output.mkdir(parents=True, exist_ok=False)
    frames = output / "frames"
    frames.mkdir()
    recording = []
    native_recording = []
    for frame in range(count):
        canvas = Image.new("RGBA", (width, height), config.get("background", "#34373d"))
        placements = []
        for instance in instances:
            manifest, atlas = assets[instance["asset"]]
            source_frames = manifest["frames"]
            index = (int(frame * manifest["fps"] / fps) + instance.get("phase", 0)) % len(source_frames)
            direction = instance.get("direction", manifest["directions"][0])
            x, y = instance["position"]
            if "route" in instance:
                x, y, direction = route_position(instance['route'], instance['speed'], frame / fps)
            row = manifest["directions"].index(direction)
            cell_width, cell_height = manifest["size"]
            sprite = atlas.crop((index * cell_width, row * cell_height,
                                 (index + 1) * cell_width, (row + 1) * cell_height))
            vx, vy = instance.get("velocity", [0, 0])
            x += vx * frame / fps
            y += vy * frame / fps
            if "wrap_x" in instance:
                low, high = instance["wrap_x"]
                x = low + (x - low) % (high - low)
            placements.append((instance.get("layer", 1), y, x, sprite, manifest["anchor"]))
        for _, y, x, sprite, anchor in sorted(placements, key=lambda p: (p[0], p[1])):
            canvas.alpha_composite(sprite, (round(x - anchor[0] * sprite.width),
                                            round(y - anchor[1] * sprite.height)))
        canvas.save(frames / f"{frame:04d}.png")
        native = canvas.convert('RGB')
        native_recording.append(native)
        recording.append(native.resize((width * scale, height * scale), Image.Resampling.NEAREST))
    recording[0].save(output / "scene.png")
    durations = [round((i + 1) * 1000 / fps) - round(i * 1000 / fps) for i in range(count)]
    recording[0].save(output / 'scene.webp', save_all=True, append_images=recording[1:],
                      duration=durations, loop=0, lossless=True, method=4)
    if scale > 1:
        native_recording[0].save(output / 'scene-native.webp', save_all=True,
            append_images=native_recording[1:],duration=durations,loop=0,lossless=True,method=4)
    if gif:
        durations = [max(10, (round((i + 1) * 100 / fps) - round(i * 100 / fps)) * 10)
                     for i in range(count)]
        recording[0].save(output / "scene.gif", save_all=True, append_images=recording[1:],
                          duration=durations, loop=0, disposal=2)
    if mp4:
        subprocess.run(["ffmpeg", "-v", "error", "-framerate", str(fps), "-i",
                        str(frames / "%04d.png"), "-vf",
                        f"scale=iw*{scale}:ih*{scale}:flags=neighbor,pad=ceil(iw/2)*2:ceil(ih/2)*2",
                        "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", str(output / "scene.mp4")], check=True)
    (output / "manifest.json").write_text(json.dumps({"fps": fps, "frames": count,
        "size": [width, height], "scale": scale, "pixels_per_unit": densities.pop()}, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mp4", action="store_true", help="record exact-rate video using FFmpeg")
    parser.add_argument('--no-gif',action='store_true',help='retain full-RGB WebP/PNG recordings without an indexed GIF')
    args = parser.parse_args()
    record(args.config.resolve(), args.output.resolve(), args.mp4, not args.no_gif)


if __name__ == "__main__":
    main()
