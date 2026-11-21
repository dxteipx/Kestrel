"""Just enough of the SVG path language to draw icons with Pillow.

Turns a path's `d` attribute into flat polygons (one per subpath). Curves and
arcs are sampled into short line segments, which is plenty at icon sizes.
"""

from __future__ import annotations

import math
import re

Point = tuple[float, float]

_NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_COMMANDS = set("MmLlHhVvCcSsQqTtAaZz")
_SEPARATORS = set(" ,\t\r\n")
_ARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "Z": 0}
_STEPS = 12


class _Reader:
    """Reads numbers one at a time. Arc flags are single digits that may touch the
    next number ("0 00-.03" is three values), so they get their own reader."""

    def __init__(self, text: str):
        self.text, self.index = text, 0

    def _skip(self) -> None:
        while self.index < len(self.text) and self.text[self.index] in _SEPARATORS:
            self.index += 1

    def done(self) -> bool:
        self._skip()
        return self.index >= len(self.text)

    def command(self) -> str | None:
        self._skip()
        if self.index < len(self.text) and self.text[self.index] in _COMMANDS:
            self.index += 1
            return self.text[self.index - 1]
        return None

    def number(self) -> float:
        self._skip()
        match = _NUMBER.match(self.text, self.index)
        if not match:
            raise ValueError(f"Expected a number at position {self.index} of the SVG path")
        self.index = match.end()
        return float(match.group())

    def flag(self) -> bool:
        self._skip()
        value = self.text[self.index]
        self.index += 1
        return value == "1"


def _cubic(p0: Point, p1: Point, p2: Point, p3: Point) -> list[Point]:
    points = []
    for i in range(1, _STEPS + 1):
        t = i / _STEPS
        u = 1 - t
        points.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                       u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return points


def _quadratic(p0: Point, p1: Point, p2: Point) -> list[Point]:
    points = []
    for i in range(1, _STEPS + 1):
        t = i / _STEPS
        u = 1 - t
        points.append((u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                       u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]))
    return points


def _arc(p0: Point, rx: float, ry: float, rotation: float, large: bool, sweep: bool, p1: Point) -> list[Point]:
    """Endpoint-to-center conversion from the SVG spec (implementation notes, B.2.4)."""
    if p0 == p1:
        return []
    if rx == 0 or ry == 0:
        return [p1]
    rx, ry = abs(rx), abs(ry)
    phi = math.radians(rotation)
    cos_phi, sin_phi = math.cos(phi), math.sin(phi)
    dx, dy = (p0[0] - p1[0]) / 2, (p0[1] - p1[1]) / 2
    x1 = cos_phi * dx + sin_phi * dy
    y1 = -sin_phi * dx + cos_phi * dy

    scale = (x1 * x1) / (rx * rx) + (y1 * y1) / (ry * ry)
    if scale > 1:
        rx, ry = rx * math.sqrt(scale), ry * math.sqrt(scale)

    numerator = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1
    denominator = rx * rx * y1 * y1 + ry * ry * x1 * x1
    factor = math.sqrt(max(numerator / denominator, 0)) if denominator else 0
    if large == sweep:
        factor = -factor
    cx1, cy1 = factor * rx * y1 / ry, -factor * ry * x1 / rx
    cx = cos_phi * cx1 - sin_phi * cy1 + (p0[0] + p1[0]) / 2
    cy = sin_phi * cx1 + cos_phi * cy1 + (p0[1] + p1[1]) / 2

    def angle(ux: float, uy: float, vx: float, vy: float) -> float:
        return math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)

    start = angle(1, 0, (x1 - cx1) / rx, (y1 - cy1) / ry)
    delta = angle((x1 - cx1) / rx, (y1 - cy1) / ry, (-x1 - cx1) / rx, (-y1 - cy1) / ry)
    if not sweep and delta > 0:
        delta -= 2 * math.pi
    elif sweep and delta < 0:
        delta += 2 * math.pi

    steps = max(4, int(abs(delta) / (math.pi / 16)))
    points = []
    for i in range(1, steps + 1):
        theta = start + delta * i / steps
        x, y = rx * math.cos(theta), ry * math.sin(theta)
        points.append((cos_phi * x - sin_phi * y + cx, sin_phi * x + cos_phi * y + cy))
    return points


def parse(d: str) -> list[list[Point]]:
    reader = _Reader(d)
    shapes: list[list[Point]] = []
    current: list[Point] = []
    position: Point = (0.0, 0.0)
    start: Point = (0.0, 0.0)
    last_control: Point | None = None
    command = ""

    while not reader.done():
        explicit = reader.command()
        if explicit:
            command = explicit
            if command in "Zz":
                if current:
                    shapes.append(current)
                current, position, last_control = [], start, None
                continue

        upper, relative = command.upper(), command.islower()
        if upper == "A":
            rx, ry, rotation = reader.number(), reader.number(), reader.number()
            large, sweep = reader.flag(), reader.flag()
            args = [rx, ry, rotation, float(large), float(sweep), reader.number(), reader.number()]
        else:
            args = [reader.number() for _ in range(_ARGS[upper])]
        ox, oy = position if relative else (0.0, 0.0)
        control: Point | None = None

        if upper == "M":
            if current:
                shapes.append(current)
            position = start = (ox + args[0], oy + args[1])
            current = [position]
            command = "l" if relative else "L"  # extra pairs after a move are line-tos
        elif upper == "L":
            position = (ox + args[0], oy + args[1])
            current.append(position)
        elif upper == "H":
            position = ((position[0] if relative else 0) + args[0], position[1])
            current.append(position)
        elif upper == "V":
            position = (position[0], (position[1] if relative else 0) + args[0])
            current.append(position)
        elif upper in "CS":
            if upper == "C":
                c1 = (ox + args[0], oy + args[1])
                c2, end = (ox + args[2], oy + args[3]), (ox + args[4], oy + args[5])
            else:
                c1 = (2 * position[0] - last_control[0], 2 * position[1] - last_control[1]) if last_control else position
                c2, end = (ox + args[0], oy + args[1]), (ox + args[2], oy + args[3])
            current += _cubic(position, c1, c2, end)
            position, control = end, c2
        elif upper in "QT":
            if upper == "Q":
                c1, end = (ox + args[0], oy + args[1]), (ox + args[2], oy + args[3])
            else:
                c1 = (2 * position[0] - last_control[0], 2 * position[1] - last_control[1]) if last_control else position
                end = (ox + args[0], oy + args[1])
            current += _quadratic(position, c1, end)
            position, control = end, c1
        elif upper == "A":
            end = (ox + args[5], oy + args[6])
            current += _arc(position, args[0], args[1], args[2], bool(args[3]), bool(args[4]), end)
            position = end
        last_control = control

    if current:
        shapes.append(current)
    return [shape for shape in shapes if len(shape) >= 3]
