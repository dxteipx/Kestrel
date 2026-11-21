from kestrel.content import brands
from kestrel.ui import svgpath


def test_square_with_relative_commands():
    shapes = svgpath.parse("M2 2h20v20H2z")
    assert shapes == [[(2, 2), (22, 2), (22, 22), (2, 22)]]


def test_compact_arc_flags_are_read_one_digit_at_a_time():
    # "0 00-1 1" is rotation 0, large-arc 0, sweep 0, then the end point (-1, 1).
    shapes = svgpath.parse("M5 5a1 1 0 00-1 1z")
    assert round(shapes[0][-1][0], 6) == 4 and round(shapes[0][-1][1], 6) == 6


def test_every_brand_logo_parses_and_stays_in_its_24px_box():
    for name, path in brands.PATHS.items():
        shapes = svgpath.parse(path)
        assert shapes, name
        points = [p for shape in shapes for p in shape]
        assert all(-0.5 <= x <= 24.5 and -0.5 <= y <= 24.5 for x, y in points), name
