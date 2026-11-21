from kestrel.core import health
from kestrel.core.system import Snapshot


def snapshot(cpu=10.0, ram=40.0, disk=50.0) -> Snapshot:
    return Snapshot(cpu=cpu, cpu_per_core=[cpu], cpu_freq_mhz=0, ram_percent=ram, ram_used=0, ram_total=1,
                    disk_percent=disk, disk_free=0, disk_total=1, net_down=0, net_up=0, processes=100,
                    uptime=0, battery=None)


def test_idle_pc_is_excellent():
    result = health.evaluate(snapshot(), [10, 12])
    assert result.score == 100
    assert result.label == "Excellent"
    assert result.tips == []


def test_worst_problem_comes_first():
    result = health.evaluate(snapshot(ram=95, disk=85), [10], temp_bytes=2 * 1024 ** 3, startup_enabled=12)
    assert result.score < 85
    assert result.tips[0].startswith("Memory is at 95%")
    assert len(result.tips) == 4


def test_score_never_goes_below_zero():
    result = health.evaluate(snapshot(cpu=100, ram=100, disk=100), [100] * 60,
                             temp_bytes=50 * 1024 ** 3, startup_enabled=40)
    assert 0 <= result.score < 50
    assert result.label == "Struggling"
