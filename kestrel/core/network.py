"""Latency checks against well-known public DNS servers, for the Games page."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from kestrel.core import shell

TARGETS = (("Cloudflare", "1.1.1.1"), ("Google", "8.8.8.8"), ("Quad9", "9.9.9.9"))

# "time=12ms", "tempo=12ms", "time<1ms" — the number is all that's language-independent.
_REPLY = re.compile(r"[=<]\s?(\d+)\s?ms\b", re.IGNORECASE)


@dataclass(frozen=True)
class PingResult:
    name: str
    host: str
    sent: int
    times: tuple[int, ...]

    @property
    def average(self) -> float | None:
        return sum(self.times) / len(self.times) if self.times else None

    @property
    def jitter(self) -> float | None:
        if len(self.times) < 2:
            return None
        return sum(abs(a - b) for a, b in zip(self.times, self.times[1:])) / (len(self.times) - 1)

    @property
    def loss(self) -> float:
        return 1 - len(self.times) / self.sent if self.sent else 1.0

    @property
    def quality(self) -> str:
        if self.average is None:
            return "Unreachable"
        if self.average < 30 and self.loss == 0:
            return "Great"
        if self.average < 70 and self.loss < 0.1:
            return "Good"
        return "Poor"


def parse(output: str) -> tuple[int, ...]:
    # Skip the summary lines at the end, which repeat numbers with "ms" too.
    replies = [line for line in output.splitlines() if "ttl" in line.lower()]
    return tuple(int(match.group(1)) for line in replies if (match := _REPLY.search(line)))


def ping(name: str, host: str, count: int = 6) -> PingResult:
    output = shell.run(["ping", "-n", str(count), "-w", "1000", host], timeout=count * 2 + 5).stdout
    return PingResult(name, host, count, parse(output))


def test_connection() -> list[PingResult]:
    with ThreadPoolExecutor(max_workers=len(TARGETS)) as pool:
        return list(pool.map(lambda target: ping(*target), TARGETS))
