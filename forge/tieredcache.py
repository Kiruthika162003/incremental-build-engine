"""Two cache tiers: the disk is fast and small, the farm is slow and vast.

The local tier answers in one tick and holds a few hundred
entries; the remote tier answers in twenty-five and holds
everything the fleet ever built. The read path tries local
first, and a remote hit promotes the entry into the local tier
on the way back, because a key asked once is a key that will be
asked again, and the second ask should cost one tick, not
twenty-five. Local eviction is least-recently-used and harmless
by design, since the remote tier still holds the bytes and the
worst case is paying the promotion again. The latency ledger
prices the whole arrangement against remote-only, counting the
ticks promotions saved on re-asks, which is the number that
justifies the local disk, and counting promotions that were
never re-asked as freight paid for nothing, which is the number
that sizes it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

LOCAL_TICKS = 1
REMOTE_TICKS = 25


@dataclass
class TieredCache:
    local_capacity: int
    local: dict[str, str] = field(default_factory=dict)
    remote: dict[str, str] = field(default_factory=dict)
    recency: list[str] = field(default_factory=list)
    ticks_paid: int = 0
    promotions: int = 0
    promoted_reused: set[str] = field(default_factory=set)
    promoted_once: dict[str, bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.local_capacity < 1:
            raise Invalid("the local tier needs at least one slot")

    def _touch(self, key: str) -> None:
        if key in self.recency:
            self.recency.remove(key)
        self.recency.append(key)

    def _promote(self, key: str, digest: str) -> None:
        if len(self.local) >= self.local_capacity:
            victim = self.recency.pop(0)
            del self.local[victim]
        self.local[key] = digest
        self._touch(key)
        self.promotions += 1
        self.promoted_once[key] = False

    def lookup(self, key: str) -> str | None:
        if key in self.local:
            self.ticks_paid += LOCAL_TICKS
            self._touch(key)
            if key in self.promoted_once:
                self.promoted_once[key] = True
            return self.local[key]
        if key in self.remote:
            self.ticks_paid += REMOTE_TICKS
            digest = self.remote[key]
            self._promote(key, digest)
            return digest
        self.ticks_paid += REMOTE_TICKS
        return None

    def store(self, key: str, digest: str) -> None:
        self.remote[key] = digest
        self._promote(key, digest)

    def ledger(self) -> str:
        reused = sum(
            1 for used in self.promoted_once.values() if used
        )
        wasted = self.promotions - reused
        saved = sum(
            (REMOTE_TICKS - LOCAL_TICKS)
            for used in self.promoted_once.values()
            if used
        )
        return (
            f"{self.ticks_paid} tick(s) paid; {self.promotions} "
            f"promotion(s), {reused} re-asked saving {saved} "
            f"tick(s), {wasted} freight paid for nothing"
        )
