"""Storage tiers: hot is for this week, cold is for the subpoena.

Artifact storage is three prices wearing one name: hot storage
answers in a tick and bills like it, nearline answers in a
hundred, cold answers tomorrow and costs almost nothing to
hold. The policy question is placement, and the placer answers
from access history rather than age, because age is a proxy
that files the wrong things: last year's release that legal
pulls monthly belongs hot, and yesterday's debug bundle nobody
opened belongs cold at the end of the week. The misplacement
bill runs both directions and the report keeps them separate,
hot-hoarding, paying premium rent on bytes nobody reads, and
cold-thrashing, paying retrieval latency on bytes that should
have stayed close, since the first wastes money quietly and
the second wastes people loudly, and a policy tuned on only
one of the two just moves the waste to the other column.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid

TIER_RENT = {"hot": 10, "nearline": 3, "cold": 1}
TIER_LATENCY = {"hot": 1, "nearline": 100, "cold": 5000}


@dataclass(frozen=True)
class StoredArtifact:
    name: str
    tier: str
    size_units: int
    reads_this_month: int

    def __post_init__(self) -> None:
        if self.tier not in TIER_RENT:
            raise Invalid(
                f"{self.name}: unknown tier {self.tier}"
            )
        if self.size_units <= 0:
            raise Invalid(f"{self.name}: size must be positive")


def right_tier(reads_this_month: int) -> str:
    if reads_this_month >= 4:
        return "hot"
    if reads_this_month >= 1:
        return "nearline"
    return "cold"


def monthly_bill(artifact: StoredArtifact) -> int:
    rent = TIER_RENT[artifact.tier] * artifact.size_units
    latency = (
        TIER_LATENCY[artifact.tier] * artifact.reads_this_month
    )
    return rent + latency


def placement_report(
    artifacts: list[StoredArtifact],
) -> str:
    if not artifacts:
        raise Invalid("an empty store needs no policy")
    hoarding = []
    thrashing = []
    placed_well = 0
    for artifact in artifacts:
        ideal = right_tier(artifact.reads_this_month)
        if artifact.tier == ideal:
            placed_well += 1
            continue
        current = monthly_bill(artifact)
        better = monthly_bill(
            StoredArtifact(
                name=artifact.name,
                tier=ideal,
                size_units=artifact.size_units,
                reads_this_month=artifact.reads_this_month,
            )
        )
        line = (
            f"{artifact.name}: {artifact.tier} -> {ideal} "
            f"saves {current - better}/month"
        )
        if TIER_RENT[artifact.tier] > TIER_RENT[ideal]:
            hoarding.append(line)
        else:
            thrashing.append(line)
    lines = [
        f"{placed_well} placed well, {len(hoarding)} "
        f"hot-hoarding, {len(thrashing)} cold-thrashing"
    ]
    if hoarding:
        lines.append("  hoarding (wastes money quietly):")
        lines.extend(f"    {line}" for line in hoarding)
    if thrashing:
        lines.append("  thrashing (wastes people loudly):")
        lines.extend(f"    {line}" for line in thrashing)
    return "\n".join(lines)
