"""Preserve source colors, validate, and assemble native-resolution sprites."""
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from settings import Settings


def cohere_shading(image: Image.Image, palettes: list[set[tuple[int, int, int]]]) -> Image.Image:
    """Merge tiny interior shade regions into supported adjacent paint regions."""
    if not palettes:
        return image
    width,height = image.size
    data = list(image.get_flattened_data())
    groups, labels = [], [-1]*len(data)
    for start,color in enumerate(data):
        if not color[3] or labels[start] >= 0:
            continue
        component, pending = [], [start]
        labels[start] = len(groups)
        while pending:
            position = pending.pop(); component.append(position)
            x,y = position%width,position//width
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    nx,ny = x+dx,y+dy
                    if (dx or dy) and 0 <= nx < width and 0 <= ny < height:
                        neighbor = ny*width+nx
                        if labels[neighbor] < 0 and data[neighbor] == color:
                            labels[neighbor] = len(groups); pending.append(neighbor)
        groups.append(component)
    result = data.copy()
    for component in groups:
        # Three native pixels distinguish a paint cluster from an isolated speck.
        # Focal accents use materials omitted from cluster_materials.
        if len(component) >= 3:
            continue
        color = data[component[0]]
        allowed = set().union(*(p for p in palettes if color[:3] in p))
        if not allowed:
            continue
        neighbors = {}
        interior = True
        for position in component:
            x,y = position%width,position//width
            if x==0 or y==0 or x==width-1 or y==height-1:
                interior = False; break
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    if not (dx or dy): continue
                    neighbor = (y+dy)*width+x+dx
                    candidate = data[neighbor]
                    if not candidate[3]: interior = False
                    if candidate[:3] in allowed and labels[neighbor] >= 0 and len(groups[labels[neighbor]]) >= 3:
                        neighbors[candidate] = neighbors.get(candidate,0)+1
        if interior and neighbors:
            replacement = max(neighbors,key=neighbors.get)
            for position in component: result[position] = replacement
    coherent = Image.new('RGBA',image.size)
    coherent.putdata(result)
    return coherent


def exterior_mask(mask: Image.Image) -> Image.Image:
    """Fill enclosed gaps for contour placement, without filling the beauty image."""
    padded = Image.new('L', (mask.width+2, mask.height+2))
    padded.paste(mask, (1,1))
    ImageDraw.floodfill(padded, (0,0), 128)
    return padded.point(lambda value: 0 if value==128 else 255).crop((1,1,mask.width+1,mask.height+1))


def outline_objects(image: Image.Image, groups: Image.Image, color: str) -> Image.Image:
    """One native pixel inside each visible asset's external silhouette."""
    if groups.mode not in ('L','P'):
        raise ValueError('object mask must contain indexed asset identities')
    if groups.size != image.size:
        raise ValueError('object mask must match the native image size')
    result = image.copy()
    for identity in set(groups.get_flattened_data()) - {0}:
        mask = groups.point(lambda value: 255 if value==identity else 0, 'L')
        box = mask.getbbox()
        if box is None:
            continue
        left,top,right,bottom = box
        box = (max(0,left-1),max(0,top-1),min(image.width,right+1),min(image.height,bottom+1))
        visible = mask.crop(box)
        filled = exterior_mask(visible)
        edge = ImageChops.subtract(filled, filled.filter(ImageFilter.MinFilter(3)))
        edge = ImageChops.multiply(edge, visible)
        result.paste((*bytes.fromhex(color),255), box, edge)
    return result


def finish_image(image: Image.Image, settings: Settings, object_mask: Image.Image | None = None) -> Image.Image:
    image = image.convert('RGBA')
    factor = settings.supersample if image.size != settings.size else 1
    expected = tuple(v * factor for v in settings.size)
    if image.size != expected:
        raise ValueError(f'wrong render size: {image.size}, expected {expected}')
    if factor > 1:
        # Integrate coverage in premultiplied RGBA; transparent RGB cannot tint
        # edge pixels. Source colors are never snapped to material shade lists.
        image = image.resize(settings.size, Image.Resampling.BOX)
    result = image.copy()
    alpha = image.getchannel('A').point(lambda a:255 if a >= 128 else 0)
    result.putalpha(alpha)
    protected = {tuple(bytes.fromhex(c)) for name,ramp in settings.palette.items()
                 if name not in settings.cluster_materials for c in ramp}
    result = cohere_shading(result,[{tuple(bytes.fromhex(c)) for c in settings.palette[name]}-protected
                                   for name in settings.cluster_materials])
    if settings.object_outline:
        if object_mask is None:
            raise ValueError('object outlines require the visible asset identity pass')
        result = outline_objects(result, object_mask, settings.object_outline)
    if settings.outline:
        contour = Image.new("RGBA", settings.size, (*bytes.fromhex(settings.outline), 0))
        filled = exterior_mask(alpha)
        expanded = filled.filter(ImageFilter.MaxFilter(3))
        contour.putalpha(ImageChops.lighter(alpha, ImageChops.multiply(expanded, ImageChops.invert(filled))))
        contour.alpha_composite(result)
        result = contour
    return result


def validate_image(image: Image.Image, settings: Settings) -> dict:
    if image.size != settings.size:
        raise ValueError(f"wrong image size: {image.size}, expected {settings.size}")
    box = image.getbbox()
    if box is None:
        raise ValueError("empty sprite")
    for pixel in image.get_flattened_data():
        if pixel[3] not in (0, 255):
            raise ValueError("sprite contains invalid alpha")
    width, height = image.size
    if settings.tileable or settings.opaque:
        if image.getchannel("A").getextrema() != (255, 255):
            raise ValueError("opaque ground must cover the full cell")
    if settings.tileable:
        horizontal = ImageChops.difference(image.crop((0, 0, 1, height)), image.crop((width - 1, 0, width, height)))
        vertical = ImageChops.difference(image.crop((0, 0, width, 1)), image.crop((0, height - 1, width, height)))
        if horizontal.convert("RGB").getbbox() or vertical.convert("RGB").getbbox():
            raise ValueError("tileable ground has mismatched opposite edges")
    elif not settings.opaque and (box[0] < 2 or box[1] < 2 or box[2] > width - 2 or box[3] > height - 2):
        raise ValueError("sprite reaches the crop margin; enlarge the canvas or adjust its anchor")
    return {"bounds": box, "tileable": settings.tileable}


def finish(directory: Path) -> None:
    settings = Settings.load(directory / "asset.json")
    manifest = json.loads((directory / "manifest.json").read_text())
    width, height = settings.size
    sprites = directory / "sprites"
    sprites.mkdir()
    atlas = Image.new("RGBA", (width * len(settings.frames), height * len(settings.directions)))
    # Contact sheet uses only integer enlargement and preserves native anchors.
    zoom = max(1, min(4, 512 // max(width, height)))
    preview_frames = []
    records = []
    images = {}
    # Indexed colors label assets in the auxiliary pass; beauty RGB is unrestricted.
    identity_palette = Image.new('P',(1,1))
    colors = [0]*768
    for identity,color in manifest.get('outline_groups',{}).items():
        start = int(identity)*3
        colors[start:start+3] = bytes.fromhex(color)
    identity_palette.putpalette(colors)
    for row, direction in enumerate(settings.directions):
        for column, frame in enumerate(settings.frames):
            name = f"{direction}-{frame:04d}.png"
            mask = None
            if settings.object_outline:
                mask = Image.open(directory/'object-masks'/name).convert('RGB').quantize(
                    palette=identity_palette, dither=Image.Dither.NONE)
            image = finish_image(Image.open(directory / "raw" / name), settings, mask)
            record = validate_image(image, settings)
            image.save(sprites / name)
            images[direction, frame] = image
            atlas.alpha_composite(image, (column * width, row * height))
            records.append({"file": f"sprites/{name}", "frame": frame, "direction": direction,
                            "atlas_rect": [column * width, row * height, width, height], **record})
    atlas.save(directory / "atlas.png")
    for frame in settings.frames:
        preview = Image.new("RGB", (width * zoom * len(settings.directions), height * zoom + 24), "#34373d")
        draw = ImageDraw.Draw(preview)
        for column, direction in enumerate(settings.directions):
            draw.text((column * width * zoom + 4, 5), f"{direction} / {frame}", fill="white")
            image = images[direction, frame].resize((width * zoom, height * zoom), Image.Resampling.NEAREST)
            preview.paste(image, (column * width * zoom, 24), image)
        preview_frames.append(preview)
    preview_frames[0].save(directory / "preview.png")
    if len(preview_frames) > 1:
        durations = [round((i+1)*1000/settings.fps)-round(i*1000/settings.fps)
                     for i in range(len(preview_frames))]
        preview_frames[0].save(directory / "preview.webp", save_all=True,
            append_images=preview_frames[1:],duration=durations,loop=0,lossless=True,method=4)
        durations = [max(10, (round((i + 1) * 100 / settings.fps) - round(i * 100 / settings.fps)) * 10) for i in range(len(preview_frames))]
        preview_frames[0].save(directory / "preview.gif", save_all=True, append_images=preview_frames[1:],
                               duration=durations, loop=0, disposal=2)
    if settings.tileable:
        tiled = Image.new("RGBA", (width * 3, height * 3))
        image = images[settings.directions[0], settings.frames[0]]
        for x in range(3):
            for y in range(3):
                tiled.alpha_composite(image, (x * width, y * height))
        tiled.resize((width * 3 * zoom, height * 3 * zoom), Image.Resampling.NEAREST).save(directory / "tiled-preview.png")
    manifest.update({"sprites": records, "atlas": "atlas.png", "preview": "preview.png",
                     "validation": {"passed": True, "sprite_count": len(records), "visual_acceptance": "unreviewed"}})
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
