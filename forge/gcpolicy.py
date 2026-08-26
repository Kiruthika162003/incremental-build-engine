"""Cache eviction: forget what the next build will not miss.

A cache that never forgets fills its disk with the outputs of
branches nobody has checked out since spring. Eviction is a bet
about the future placed with records of the past: each entry
carries its last-hit tick and its rebuild cost, and the two
policies on offer disagree about what matters. Least-recently-used
forgets the coldest entry and is right when access predicts
access; cost-aware forgets the entry with the lowest cost per byte
and is right when the disk is full of cheap fat. The eviction
ledger records every forgotten key with the reason, so the day a
build misses on something evicted last week, the postmortem reads
the bet that lost rather than reconstructing it, and the meter
counts exactly those regret misses because an eviction policy is
judged by nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class TrackedEntry:
    key: str
    size: int
    cost: int
    last_hit: int


@dataclass
class EvictingCache:
    capacity_bytes: int
    policy: str = "lru"
    entries: dict[str, TrackedEntry] = field(default_factory=dict)
    evicted_log: list[tuple[str, str]] = field(default_factory=list)
    regret_misses: int = 0
    forgotten: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.capacity_bytes <= 0:
            raise Invalid("a cache needs room")
        if self.policy not in ("lru", "cost-aware"):
            raise Invalid(f"unknown policy {self.policy}")

    def held_bytes(self) -> int:
        return sum(entry.size for entry in self.entries.values())

    def admit(self, key: str, size: int, cost: int, now: int) -> None:
        if size > self.capacity_bytes:
            raise Invalid(
                f"{key} alone exceeds the cache: {size} bytes "
                f"against {self.capacity_bytes}"
            )
        self.entries[key] = TrackedEntry(
            key=key, size=size, cost=cost, last_hit=now
        )
        self.forgotten.discard(key)
        while self.held_bytes() > self.capacity_bytes:
            self._evict_one()

    def _evict_one(self) -> None:
        victims = [
            entry for entry in self.entries.values()
        ]
        if self.policy == "lru":
            victim = min(
                victims, key=lambda entry: (entry.last_hit, entry.key)
            )
            reason = f"lru: cold since {victim.last_hit}"
        else:
            victim = min(
                victims,
                key=lambda entry: (
                    entry.cost / entry.size,
                    entry.key,
                ),
            )
            reason = (
                f"cost-aware: {entry_rate(victim)} ticks per byte"
            )
        del self.entries[victim.key]
        self.forgotten.add(victim.key)
        self.evicted_log.append((victim.key, reason))

    def lookup(self, key: str, now: int) -> bool:
        entry = self.entries.get(key)
        if entry is not None:
            entry.last_hit = now
            return True
        if key in self.forgotten:
            self.regret_misses += 1
        return False

    def postmortem(self, key: str) -> str:
        for name, reason in self.evicted_log:
            if name == key:
                return f"{key} was forgotten: {reason}"
        return f"{key} was never evicted; it was never here"

    def judgement(self) -> str:
        return (
            f"{len(self.evicted_log)} evictions, "
            f"{self.regret_misses} regret misses; the policy is "
            f"judged by nothing else"
        )


def entry_rate(entry: TrackedEntry) -> float:
    return round(entry.cost / entry.size, 4)
