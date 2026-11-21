"""Recognise trusted PCs by their graphics card.

Every NVIDIA GPU has a unique UUID. Kestrel never stores or publishes it: only a
salted SHA-256 fingerprint goes into `cloud.OWNER_DEVICES`, which can't be turned
back into the UUID.

To trust another PC, run this on it and add the printed fingerprint:

    python -m kestrel.core.device
"""

from __future__ import annotations

import hashlib
from functools import lru_cache

from kestrel import cloud
from kestrel.core import gpu, shell

_SALT = "kestrel-owner:"


def fingerprint(gpu_uuid: str) -> str:
    return hashlib.sha256(f"{_SALT}{gpu_uuid.strip().upper()}".encode()).hexdigest()


@lru_cache(maxsize=1)
def gpu_uuids() -> tuple[str, ...]:
    tool = gpu._nvidia_smi()
    if not tool:
        return ()
    try:
        output = shell.run([tool, "--query-gpu=uuid", "--format=csv,noheader"], timeout=5).stdout
    except (OSError, TimeoutError):
        return ()
    return tuple(line.strip() for line in output.splitlines() if line.strip().upper().startswith("GPU-"))


def is_owner_device() -> bool:
    trusted = set(cloud.OWNER_DEVICES)
    return bool(trusted) and any(fingerprint(uuid) in trusted for uuid in gpu_uuids())


if __name__ == "__main__":
    uuids = gpu_uuids()
    if not uuids:
        print("No NVIDIA GPU found — this PC can't be marked as trusted.")
    for uuid in uuids:
        print(fingerprint(uuid))
