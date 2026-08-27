"""Load testing the farm: unrealistic traffic certifies the wrong farm.

A load test that hammers the farm with ten thousand identical
compiles proves the farm survives ten thousand identical
compiles, which production will never send: production is a
mix, compiles and links and tests in proportions the meters
already know, and a synthetic load earns trust by matching
that shape before anyone reads its throughput number. The
grader compares the synthetic mix against the production mix
class by class, names each divergence with its direction,
over-represented or missing, and computes a realism score
that gates the results: below the bar, the throughput
number is withheld, not footnoted, because a wrong number
with a caveat outlives the caveat in every meeting it is
quoted in. The passing test reports throughput with its
realism attached, one line, inseparable.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid

REALISM_BAR = 0.8


@dataclass(frozen=True)
class TrafficMix:
    shares: dict[str, float]

    def __post_init__(self) -> None:
        total = sum(self.shares.values())
        if abs(total - 1.0) > 1e-9:
            raise Invalid(
                f"shares must sum to 1, got {total:.2f}"
            )


def realism(
    production: TrafficMix, synthetic: TrafficMix
) -> float:
    classes = set(production.shares) | set(synthetic.shares)
    return sum(
        min(
            production.shares.get(kind, 0.0),
            synthetic.shares.get(kind, 0.0),
        )
        for kind in classes
    )


def divergences(
    production: TrafficMix, synthetic: TrafficMix
) -> list[str]:
    found = []
    classes = sorted(
        set(production.shares) | set(synthetic.shares)
    )
    for kind in classes:
        real = production.shares.get(kind, 0.0)
        fake = synthetic.shares.get(kind, 0.0)
        if abs(real - fake) < 0.05:
            continue
        direction = (
            "over-represented"
            if fake > real
            else ("missing" if fake == 0 else "under-represented")
        )
        found.append(
            f"{kind}: {fake:.0%} synthetic against "
            f"{real:.0%} production ({direction})"
        )
    return found


def grade(
    production: TrafficMix,
    synthetic: TrafficMix,
    measured_throughput: int,
) -> str:
    score = realism(production, synthetic)
    if score < REALISM_BAR:
        lines = [
            f"WITHHELD: realism {score:.0%} under the "
            f"{REALISM_BAR:.0%} bar; a wrong number with a "
            "caveat outlives the caveat"
        ]
        lines.extend(
            f"  {line}"
            for line in divergences(production, synthetic)
        )
        return "\n".join(lines)
    return (
        f"throughput {measured_throughput}/tick at realism "
        f"{score:.0%}; one line, inseparable"
    )
