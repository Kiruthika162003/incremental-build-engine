"""Test sharding: the suite's wall clock is its worst shard, so pack well.

A thousand tests across eight workers finish when the slowest
worker does, and naive round-robin sharding routinely builds one
shard twice as heavy as the rest. The packer sorts tests by
recorded duration, longest first, and assigns each to the lightest
shard so far, which is the classic greedy bound within
one-longest-test of optimal, and the skew line prints how far from
perfect the packing landed. Duration records age: a test that grew
threefold since its recording quietly recreates the problem, so
the staleness check compares recorded against observed after each
run and names the drifted tests, because a sharding scheme is only
as good as its scale, and scales drift.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid


@dataclass
class ShardPlan:
    shards: list[list[str]]
    loads: list[int]

    def skew(self) -> float:
        heaviest = max(self.loads)
        lightest = min(self.loads)
        if heaviest == 0:
            raise Invalid("an empty plan has no skew")
        return round((heaviest - lightest) / heaviest, 4)

    def wall_clock(self) -> int:
        return max(self.loads)

    def line(self) -> str:
        return (
            f"{len(self.shards)} shards, wall clock "
            f"{self.wall_clock()}, skew {self.skew():.1%}"
        )


def pack(durations: dict[str, int], shard_count: int) -> ShardPlan:
    if shard_count <= 0:
        raise Invalid("shard_count must be positive")
    if not durations:
        raise Invalid("no tests to shard")
    if any(cost < 0 for cost in durations.values()):
        raise Invalid("durations cannot be negative")
    shards: list[list[str]] = [[] for _ in range(shard_count)]
    loads = [0] * shard_count
    ordered = sorted(
        durations.items(), key=lambda row: (-row[1], row[0])
    )
    for name, cost in ordered:
        lightest = min(range(shard_count), key=lambda i: loads[i])
        shards[lightest].append(name)
        loads[lightest] += cost
    return ShardPlan(shards=shards, loads=loads)


def round_robin(
    durations: dict[str, int], shard_count: int
) -> ShardPlan:
    """The naive packer, kept for the comparison it loses."""
    shards: list[list[str]] = [[] for _ in range(shard_count)]
    loads = [0] * shard_count
    for index, name in enumerate(sorted(durations)):
        shards[index % shard_count].append(name)
        loads[index % shard_count] += durations[name]
    return ShardPlan(shards=shards, loads=loads)


def drifted_scales(
    recorded: dict[str, int],
    observed: dict[str, int],
    factor: float = 2.0,
) -> list[str]:
    drifted = []
    for name in sorted(recorded):
        seen = observed.get(name)
        if seen is None:
            continue
        was = max(recorded[name], 1)
        if seen / was >= factor or was / max(seen, 1) >= factor:
            drifted.append(
                f"{name}: recorded {recorded[name]}, observed {seen}"
            )
    return drifted
