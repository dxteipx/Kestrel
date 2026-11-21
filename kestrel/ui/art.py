"""Graphics drawn with Pillow: gradients, gauges, charts, covers and the logo.

Everything is rendered at the screen's real scale with extra supersampling and
then handed to CustomTkinter as a CTkImage, so edges stay smooth at any DPI.
Functions that take colors expect resolved hex strings, never (light, dark) pairs.
"""

from __future__ import annotations

import math
import os
from functools import lru_cache
from pathlib import Path
from typing import Sequence

import customtkinter as ctk
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

_SUPERSAMPLE = 3
_scale = 1.0

Series = tuple[Sequence[float], str, str]


def set_scale(value: float) -> None:
    global _scale
    _scale = value


def logical(physical_pixels: int) -> int:
    return round(physical_pixels / _scale)


def _px(value: float) -> int:
    return max(1, round(value * _scale))


def _rgb(color: str) -> tuple[int, int, int]:
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def _canvas(width: int, height: int, ss: int = _SUPERSAMPLE) -> tuple[int, int, float]:
    return _px(width) * ss, _px(height) * ss, _scale * ss


def _finish(image: Image.Image, width: int, height: int) -> ctk.CTkImage:
    image = image.resize((_px(width), _px(height)), Image.LANCZOS)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))


# --- Fonts --------------------------------------------------------------------

_FONT_DIR = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
_FONTS = {
    "display": (("bahnschrift.ttf", "SemiBold"), ("segoeuisb.ttf", None), ("segoeuib.ttf", None)),
    "body": (("segoeui.ttf", None),),
    "bold": (("segoeuib.ttf", None),),
}


@lru_cache(maxsize=64)
def _font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    for file, variation in _FONTS[kind]:
        try:
            font = ImageFont.truetype(str(_FONT_DIR / file), size)
        except OSError:
            continue
        if variation:
            try:
                font.set_variation_by_name(variation)
            except (OSError, ValueError):
                pass
        return font
    return ImageFont.load_default(size)


# --- Primitives ---------------------------------------------------------------

def gradient(size: tuple[int, int], start: str, end: str, direction: str = "diagonal") -> Image.Image:
    width, height = size
    a, b = _rgb(start), _rgb(end)
    ramp = Image.new("RGB", (256, 1))
    ramp.putdata([tuple(round(a[i] + (b[i] - a[i]) * t / 255) for i in range(3)) for t in range(256)])
    if direction == "horizontal":
        return ramp.resize((width, height), Image.BILINEAR)
    if direction == "vertical":
        return ramp.resize((height, width), Image.BILINEAR).transpose(Image.TRANSPOSE)
    wide = ramp.resize((width + height, height), Image.BILINEAR)
    return wide.transform((width, height), Image.AFFINE, (1, 1, 0, 0, 1, 0), Image.BILINEAR)


def _rounded_mask(width: int, height: int, radius: float) -> Image.Image:
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, width - 1, height - 1], radius=radius, fill=255)
    return mask


@lru_cache(maxsize=512)
def tile(width: int, height: int, radius: int, start: str, end: str, lighten: float = 0.0) -> ctk.CTkImage:
    """A rounded gradient rectangle (buttons, chips, swatches)."""
    w, h, s = _canvas(width, height)
    image = gradient((w, h), start, end).convert("RGBA")
    if lighten:
        image = Image.blend(image, Image.new("RGBA", (w, h), (255, 255, 255, 255)), lighten)
    image.putalpha(_rounded_mask(w, h, radius * s))
    return _finish(image, width, height)


@lru_cache(maxsize=64)
def blank(width: int, height: int) -> ctk.CTkImage:
    image = Image.new("RGBA", (_px(width), _px(height)), (0, 0, 0, 0))
    return ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))


@lru_cache(maxsize=512)
def flat(width: int, height: int, radius: int, color: str) -> ctk.CTkImage:
    return tile(width, height, radius, color, color)


@lru_cache(maxsize=1024)
def bar(width: int, height: int, fraction: float, start: str, end: str, track: str) -> ctk.CTkImage:
    w, h, s = _canvas(width, height)
    image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(image).rounded_rectangle([0, 0, w - 1, h - 1], radius=h / 2, fill=_rgb(track))
    filled = round(w * max(0.0, min(fraction, 1.0)))
    if filled >= h:
        fill = gradient((w, h), start, end, "horizontal").convert("RGBA")
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, filled - 1, h - 1], radius=h / 2, fill=255)
        image.paste(fill, (0, 0), mask)
    return _finish(image, width, height)


# --- Gauges -------------------------------------------------------------------

def _draw_ring(image: Image.Image, center: tuple[float, float], diameter: float, thickness: float,
               fraction: float, start: str, end: str, track: tuple[int, ...], glow: float) -> None:
    cx, cy = center
    radius = diameter / 2
    box = [cx - radius, cy - radius, cx + radius, cy + radius]
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).arc(box, 0, 360, fill=track, width=round(thickness))

    fraction = max(0.0, min(fraction, 1.0))
    if fraction > 0.002:
        mask = Image.new("L", image.size, 0)
        draw = ImageDraw.Draw(mask)
        end_angle = -90 + 360 * fraction
        draw.arc(box, -90, end_angle, fill=255, width=round(thickness))
        centerline = radius - thickness / 2
        for angle in (-90, end_angle):
            x = cx + centerline * math.cos(math.radians(angle))
            y = cy + centerline * math.sin(math.radians(angle))
            draw.ellipse([x - thickness / 2, y - thickness / 2, x + thickness / 2, y + thickness / 2], fill=255)

        color = gradient(image.size, start, end).convert("RGBA")
        if glow:
            halo = color.copy()
            halo.putalpha(mask.filter(ImageFilter.GaussianBlur(thickness * 0.9)).point(lambda v: int(v * glow)))
            layer.alpha_composite(halo)
        color.putalpha(mask)
        layer.alpha_composite(color)
    image.alpha_composite(layer)


def gauge(size: int, fraction: float, value: str, caption: str, start: str, end: str,
          background: str, text: str, muted: str, track: str, thickness: int = 9) -> ctk.CTkImage:
    w, _, s = _canvas(size, size)
    image = Image.new("RGBA", (w, w), _rgb(background) + (255,))
    margin = (thickness + 3) * s
    _draw_ring(image, (w / 2, w / 2), w - 2 * margin, thickness * s, fraction, start, end,
               _rgb(track) + (255,), glow=0.35)
    draw = ImageDraw.Draw(image)
    draw.text((w / 2, w / 2 - 2 * s), value, font=_font("display", round(size * 0.25 * s)),
              fill=_rgb(text), anchor="mm")
    if caption:
        draw.text((w / 2, w / 2 + size * 0.19 * s), caption, font=_font("bold", round(size * 0.1 * s)),
                  fill=_rgb(muted), anchor="mm")
    return _finish(image, size, size)


# --- Charts -------------------------------------------------------------------

def _smooth(points: list[tuple[float, float]], steps: int = 6) -> list[tuple[float, float]]:
    if len(points) < 3:
        return points
    padded = [points[0], *points, points[-1]]
    result = []
    for i in range(1, len(padded) - 2):
        p0, p1, p2, p3 = padded[i - 1], padded[i], padded[i + 1], padded[i + 2]
        for step in range(steps):
            t = step / steps
            t2, t3 = t * t, t * t * t
            result.append(tuple(
                0.5 * (2 * p1[k] + (p2[k] - p0[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2
                       + (3 * p1[k] - p0[k] - 3 * p2[k] + p3[k]) * t3)
                for k in (0, 1)
            ))
    result.append(points[-1])
    return result


def area_chart(width: int, height: int, series: Sequence[Series], capacity: int, background: str,
               grid: str | None = None, maximum: float | None = None) -> ctk.CTkImage:
    w, h, s = _canvas(width, height, ss=2)
    image = Image.new("RGBA", (w, h), _rgb(background) + (255,))
    draw = ImageDraw.Draw(image)

    if grid:
        for row in (1, 2, 3):
            y = h * row / 4
            for x in range(0, w, round(9 * s)):
                draw.line([(x, y), (x + 3 * s, y)], fill=_rgb(grid), width=max(1, round(s / 2)))

    peak = maximum or max([max(v) for v, _, _ in series if v] + [1.0]) * 1.2
    pad = 4 * s
    fade = ImageOps.invert(Image.linear_gradient("L")).resize((w, h)).point(lambda v: int(v * 0.5))
    step = w / max(capacity - 1, 1)

    for values, start, end in series:
        values = list(values)
        if len(values) < 2:
            continue
        offset = w - (len(values) - 1) * step
        points = [(offset + i * step, h - pad - (min(v, peak) / peak) * (h - 2 * pad)) for i, v in enumerate(values)]
        curve = [(x, min(max(y, pad / 2), h - 1)) for x, y in _smooth(points)]
        color = gradient((w, h), start, end, "horizontal").convert("RGBA")

        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).polygon([*curve, (curve[-1][0], h), (curve[0][0], h)], fill=255)
        area = color.copy()
        area.putalpha(ImageChops.multiply(mask, fade))
        image.alpha_composite(area)

        line_mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(line_mask).line(curve, fill=255, width=round(2.2 * s), joint="curve")
        color.putalpha(line_mask)
        image.alpha_composite(color)

        x, y = curve[-1]
        x = min(x, w - 5 * s)
        draw.ellipse([x - 4.5 * s, y - 4.5 * s, x + 4.5 * s, y + 4.5 * s], fill=_rgb(end))
        draw.ellipse([x - 2 * s, y - 2 * s, x + 2 * s, y + 2 * s], fill=_rgb(background))

    image = image.resize((_px(width), _px(height)), Image.LANCZOS)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))


# --- Aurora backdrops ---------------------------------------------------------

def _aurora_layer(w: int, h: int, blobs: Sequence[tuple[float, float, float, str, int]]) -> Image.Image:
    """Soft blurred color blobs. Drawn small and scaled up, since they're blurry anyway."""
    small_w, small_h = max(w // 8, 8), max(h // 8, 8)
    layer = Image.new("RGBA", (small_w, small_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for cx, cy, r, color, alpha in blobs:
        radius = r * small_h
        draw.ellipse([cx * small_w - radius, cy * small_h - radius, cx * small_w + radius, cy * small_h + radius],
                     fill=_rgb(color) + (alpha,))
    layer = layer.filter(ImageFilter.GaussianBlur(small_h * 0.3))
    return layer.resize((w, h), Image.BICUBIC)


def hero(width: int, height: int, score: int, label: str, start: str, end: str,
         base: str, border: str, dark: bool) -> ctk.CTkImage:
    w, h, s = _canvas(width, height, ss=2)
    image = Image.new("RGBA", (w, h), _rgb(base) + (255,))

    strength = 1.0 if dark else 0.92
    layer = _aurora_layer(w, h, [
        (0.80, 0.25, 0.95, start, int(210 * strength)),
        (0.95, 0.95, 0.85, end, int(190 * strength)),
        (0.62, 1.05, 0.55, end, int(90 * strength)),
        (0.70, -0.1, 0.45, start, int(120 * strength)),
    ])
    ramp = Image.linear_gradient("L").rotate(90, expand=True).resize((w, h))
    ramp = ramp.point(lambda v: 0 if v < 150 else min(255, int((v - 150) * 2.6)))
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), ramp))
    image.alpha_composite(layer)

    diameter = h * 0.66
    center = (w - h * 0.62, h / 2)
    if dark:
        ring, track, ink = ("#ffffff", "#ffffff"), (255, 255, 255, 46), (255, 255, 255)
    else:
        ring, track, ink = (start, end), (255, 255, 255, 200), (18, 19, 28)
    _draw_ring(image, center, diameter, 10 * s, score / 100, *ring, track, glow=0.0 if dark else 0.3)
    draw = ImageDraw.Draw(image)
    draw.text((center[0], center[1] - 6 * s), str(score), font=_font("display", round(diameter * 0.36)),
              fill=ink, anchor="mm")
    draw.text((center[0], center[1] + diameter * 0.2), label.upper(), font=_font("bold", round(diameter * 0.1)),
              fill=ink, anchor="mm")

    radius = 20 * s
    outline = ImageDraw.Draw(image)
    outline.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, outline=_rgb(border), width=max(1, round(s)))
    image.putalpha(_rounded_mask(w, h, radius))
    return _finish(image, width, height)


@lru_cache(maxsize=256)
def cover(width: int, height: int, title: str, start: str, end: str, base: str) -> ctk.CTkImage:
    """Generated cover art for games without one: aurora blobs and a big initial."""
    w, h, s = _canvas(width, height, ss=2)
    image = Image.new("RGBA", (w, h), _rgb(base) + (255,))
    seed = sum(map(ord, title))
    image.alpha_composite(_aurora_layer(w, h, [
        (0.15 + (seed % 7) / 10, 0.2, 1.0, start, 230),
        (0.9 - (seed % 5) / 10, 0.95, 0.9, end, 220),
        (0.5, 0.5, 0.5, start, 120),
    ]))
    letter = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    initial = (title.strip()[:1] or "?").upper()
    ImageDraw.Draw(letter).text((w - 16 * s, h + 14 * s), initial, font=_font("display", round(h * 1.1)),
                                fill=(255, 255, 255, 46), anchor="rs")
    image.alpha_composite(letter)
    image.putalpha(_rounded_mask(w, h, 12 * s))
    return _finish(image, width, height)


# --- Logo ---------------------------------------------------------------------

_WING = [(0.17, 0.60), (0.50, 0.30), (0.83, 0.60), (0.70, 0.66), (0.50, 0.48), (0.30, 0.66)]
_TAIL = [(0.50, 0.56), (0.58, 0.68), (0.50, 0.82), (0.42, 0.68)]


def logo_image(pixels: int, start: str, end: str) -> Image.Image:
    """The Kestrel mark — a hovering bird reduced to a chevron and a diamond."""
    big = pixels * 4
    image = gradient((big, big), start, end).convert("RGBA")
    image.putalpha(_rounded_mask(big, big, big * 0.28))
    draw = ImageDraw.Draw(image)
    for shape in (_WING, _TAIL):
        draw.polygon([(x * big, y * big) for x, y in shape], fill=(255, 255, 255, 245))
    return image.resize((pixels, pixels), Image.LANCZOS)


@lru_cache(maxsize=16)
def logo(size: int, start: str, end: str) -> ctk.CTkImage:
    image = logo_image(_px(size), start, end)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))


def banner(width: int, height: int, title: str, caption: str, start: str, end: str, base: str,
           radius: int = 0) -> ctk.CTkImage:
    """A tall aurora panel with the logo and name — the installer's side art."""
    w, h, s = _canvas(width, height, ss=2)
    image = Image.new("RGBA", (w, h), _rgb(base) + (255,))
    image.alpha_composite(_aurora_layer(w, h, [
        (0.2, 0.15, 0.55, start, 235),
        (0.9, 0.55, 0.5, end, 215),
        (0.3, 0.95, 0.45, start, 170),
    ]))
    mark = logo_image(round(64 * s), start, end)
    image.alpha_composite(mark, (round(28 * s), round(36 * s)))
    draw = ImageDraw.Draw(image)
    draw.text((28 * s, h - 70 * s), title, font=_font("display", round(30 * s)), fill=(255, 255, 255), anchor="ls")
    draw.text((29 * s, h - 46 * s), caption, font=_font("body", round(13 * s)), fill=(255, 255, 255, 220),
              anchor="ls")
    if radius:
        image.putalpha(_rounded_mask(w, h, radius * s))
    return _finish(image, width, height)


_GOOGLE_COLORS = (("#4285F4", -40, 35), ("#34A853", 35, 140), ("#FBBC05", 140, 215), ("#EA4335", 215, 320))


@lru_cache(maxsize=32)
def brand_icon(name: str, size: int, color: str) -> ctk.CTkImage:
    """A brand mark from its 24x24 SVG path, filled even-odd so the holes stay open."""
    from kestrel.content import brands
    from kestrel.ui import svgpath

    w, _, s = _canvas(size, size, ss=4)
    scale = w / 24
    mask = Image.new("L", (w, w), 0)
    for shape in svgpath.parse(brands.PATHS[name]):
        layer = Image.new("L", (w, w), 0)
        ImageDraw.Draw(layer).polygon([(x * scale, y * scale) for x, y in shape], fill=255)
        mask = ImageChops.logical_xor(mask.convert("1"), layer.convert("1")).convert("L")

    if name == "google":
        # Google's "G" is four colours; paint the single-colour mark by angle around its centre.
        image = Image.new("RGBA", (w, w), (0, 0, 0, 0))
        box = [-w * 0.5, -w * 0.5, w * 1.5, w * 1.5]
        for hex_color, start, end in _GOOGLE_COLORS:
            sector = Image.new("L", (w, w), 0)
            ImageDraw.Draw(sector).pieslice(box, start, end, fill=255)
            paint = Image.new("RGBA", (w, w), _rgb(hex_color) + (255,))
            paint.putalpha(ImageChops.multiply(mask, sector))
            image.alpha_composite(paint)
    else:
        image = Image.new("RGBA", (w, w), _rgb(color) + (0,))
        image.putalpha(mask)
    return _finish(image, size, size)


@lru_cache(maxsize=128)
def photo(path: str, width: int, height: int, radius: int = 12) -> ctk.CTkImage:
    """A picture cropped to fill the box (like CSS object-fit: cover), with rounded corners."""
    w, h, s = _canvas(width, height, ss=1)
    with Image.open(path) as source:
        image = ImageOps.fit(source.convert("RGBA"), (w, h), Image.LANCZOS, centering=(0.5, 0.35))
    image.putalpha(_rounded_mask(w, h, radius * s))
    return ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))


def write_icon(path: Path, start: str, end: str) -> None:
    image = logo_image(256, start, end)
    image.save(path, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
