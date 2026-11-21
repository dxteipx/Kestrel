from kestrel import cloud
from kestrel.core import device

UUID = "GPU-12345678-90ab-cdef-1234-567890abcdef"


def test_fingerprint_is_stable_and_hides_the_uuid():
    first = device.fingerprint(UUID)
    assert first == device.fingerprint(UUID.lower() + "  ")
    assert len(first) == 64 and "12345678" not in first


def test_owner_device_matches_by_fingerprint(monkeypatch):
    monkeypatch.setattr(device, "gpu_uuids", lambda: (UUID,))
    monkeypatch.setattr(cloud, "OWNER_DEVICES", (device.fingerprint(UUID),))
    assert device.is_owner_device()


def test_other_pcs_and_empty_lists_are_not_owners(monkeypatch):
    monkeypatch.setattr(device, "gpu_uuids", lambda: ("GPU-other",))
    monkeypatch.setattr(cloud, "OWNER_DEVICES", (device.fingerprint(UUID),))
    assert not device.is_owner_device()
    monkeypatch.setattr(cloud, "OWNER_DEVICES", ())
    assert not device.is_owner_device()
