"""Geo-replicated caches: the artifact exists, just not here yet.

Two regions, one cache namespace, and a replication stream
between them that runs behind by a lag the operators pretend is
zero. The model makes the lag a number: an upload lands in its
home region at once and in the other region after the lag, so a
lookup is answered from three possible states, present, in
transit, or absent, and the in-transit answer is the one naive
caches get wrong by reporting a plain miss and triggering a
rebuild of bytes already crossing the ocean. The policy knob is
per caller: interactive builds serve-local and rebuild rather
than wait, because a developer's seconds outrank freight, while
release builds wait for the replica, because rebuilding a
release artifact in a second region forfeits the identity that
promotion ladders depend on. The read-your-writes guarantee is
enforced at home: the region that uploaded never misses its own
upload, whatever the stream is doing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

REGIONS = ("us", "eu")


@dataclass
class GeoCache:
    replication_lag: int
    entries: dict[tuple[str, str], int] = field(
        default_factory=dict
    )
    rebuilds_triggered: int = 0
    waits_served: int = 0

    def __post_init__(self) -> None:
        if self.replication_lag < 0:
            raise Invalid("lag cannot be negative")

    def upload(self, key: str, region: str, now: int) -> None:
        if region not in REGIONS:
            raise Invalid(f"unknown region {region}")
        self.entries[(key, region)] = now
        other = next(r for r in REGIONS if r != region)
        self.entries[(key, other)] = now + self.replication_lag

    def state(self, key: str, region: str, now: int) -> str:
        arrival = self.entries.get((key, region))
        if arrival is None:
            return "absent"
        if arrival <= now:
            return "present"
        return f"in transit, arrives at {arrival}"

    def lookup(
        self, key: str, region: str, now: int, caller: str
    ) -> str:
        if caller not in ("interactive", "release"):
            raise Invalid(f"unknown caller class {caller}")
        state = self.state(key, region, now)
        if state == "present":
            return f"{key}: hit in {region}"
        if state == "absent":
            self.rebuilds_triggered += 1
            return f"{key}: true miss in {region}, rebuild"
        arrival = self.entries[(key, region)]
        if caller == "interactive":
            self.rebuilds_triggered += 1
            return (
                f"{key}: crossing the ocean until {arrival}; "
                "the developer's seconds outrank freight, "
                "rebuild locally"
            )
        self.waits_served += 1
        return (
            f"{key}: release build waits until {arrival}, "
            "because rebuilding elsewhere forfeits the identity "
            "the ladder depends on"
        )

    def ledger(self) -> str:
        return (
            f"{self.rebuilds_triggered} rebuild(s) triggered, "
            f"{self.waits_served} wait(s) served"
        )
