"""Seven-step soft palette fill for oblique RPG sprites."""

SHADE_STOPS = (0, .12, .26, .4, .54, .68, .82)


def soft_ramp(anchors: list[str]) -> list[str]:
    """Expand four dark-to-light sRGB anchors into seven softly filled shades."""
    if len(anchors) != 4:
        raise ValueError("soft fill requires four material anchors")
    colors = [tuple(bytes.fromhex(color)) for color in anchors]
    softened = [tuple(round(.84 * v + .16 * mid) for v, mid in zip(color, colors[2])) for color in colors]
    shades = []
    for a, b in zip(softened, softened[1:]):
        shades.extend([a, tuple(round((x + y) / 2) for x, y in zip(a, b))])
    shades.append(softened[-1])
    return [bytes(color).hex() for color in shades]
