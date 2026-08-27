"""The bloom gate: answer "definitely not" locally, pay the trip only for maybe.

Most remote cache lookups on a cold branch are misses, and a
miss over the network costs the same round trip as a hit
without the consolation prize. The bloom filter sits in front:
a compact bitmap the remote publishes, in which every stored
key sets a handful of deterministic bits, so absence is
provable locally, if any bit is clear the key is definitely
not there, while presence is only ever a maybe that still pays
the trip. The economics run on the false positive rate, maybes
that travel and miss anyway, and the gate meters it honestly
against the filter's advertised rate, because an overfull
bitmap quietly degrades toward always-maybe, at which point
the gate costs memory and saves nothing, and the meter is how
someone notices before the dashboard does.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.content import digest_text
from forge.errors import Invalid

BITS = 256
HASHES = 3
ROUND_TRIP_TICKS = 25


def _positions(key: str) -> list[int]:
    digest = digest_text(key)
    return [
        int(digest[8 * index : 8 * index + 8], 16) % BITS
        for index in range(HASHES)
    ]


@dataclass
class BloomGate:
    bitmap: set[int] = field(default_factory=set)
    remote_keys: set[str] = field(default_factory=set)
    skipped_trips: int = 0
    paid_trips: int = 0
    false_positives: int = 0

    def publish(self, key: str) -> None:
        self.remote_keys.add(key)
        self.bitmap.update(_positions(key))

    def lookup(self, key: str) -> str:
        if any(
            position not in self.bitmap
            for position in _positions(key)
        ):
            self.skipped_trips += 1
            return (
                f"{key}: definitely not remote; the trip is "
                "skipped"
            )
        self.paid_trips += 1
        if key in self.remote_keys:
            return f"{key}: maybe said the filter, hit said the cache"
        self.false_positives += 1
        return (
            f"{key}: a maybe that travelled and missed; the "
            "false positive column pays for the bitmap"
        )

    def ledger(self) -> str:
        total = self.skipped_trips + self.paid_trips
        if total == 0:
            raise Invalid("no lookups to price")
        saved = self.skipped_trips * ROUND_TRIP_TICKS
        rate = (
            self.false_positives / self.paid_trips
            if self.paid_trips
            else 0.0
        )
        line = (
            f"{self.skipped_trips} trip(s) skipped saving "
            f"{saved} tick(s), {self.paid_trips} paid, "
            f"{self.false_positives} false positive(s) "
            f"({rate:.0%} of travels)"
        )
        fill = len(self.bitmap) / BITS
        if fill > 0.6:
            line += (
                f"; the bitmap is {fill:.0%} full and drifting "
                "toward always-maybe, at which point the gate "
                "costs memory and saves nothing"
            )
        return line
