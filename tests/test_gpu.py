from kestrel.core import gpu


def test_parse_full_line():
    stats = gpu.parse("NVIDIA GeForce RTX 4070, 37, 55, 2048, 12282, 120.5")
    assert stats.name == "NVIDIA GeForce RTX 4070"
    assert stats.usage == 37
    assert stats.temperature == 55
    assert round(stats.memory_fraction, 3) == round(2048 / 12282, 3)
    assert stats.power_watts == 120.5


def test_parse_handles_unsupported_fields():
    stats = gpu.parse("NVIDIA GeForce GTX 1050, 5, 40, 300, 2048, [N/A]")
    assert stats.power_watts is None


def test_parse_rejects_garbage():
    assert gpu.parse("NVIDIA-SMI has failed") is None
