from kestrel import formatting as fmt


def test_size_picks_a_readable_unit():
    assert fmt.size(512) == "512 B"
    assert fmt.size(1536) == "1.5 KB"
    assert fmt.size(5 * 1024 ** 3) == "5.0 GB"


def test_rate_and_percent():
    assert fmt.rate(2048) == "2.0 KB/s"
    assert fmt.percent(42.4) == "42%"


def test_duration_uses_the_two_largest_units():
    assert fmt.duration(59) == "0m"
    assert fmt.duration(3 * 3600 + 25 * 60) == "3h 25m"
    assert fmt.duration(2 * 86400 + 5 * 3600) == "2d 5h"
