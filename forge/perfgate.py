"""Performance gates that know their own noise, or decline to gate.

A benchmark that swings 8 percent between identical runs cannot
detect a 3 percent regression; wiring it to a gate anyway builds
a random number generator with opinions, and the team learns to
click past it, which un-builds the gate. Every benchmark must
first earn the right to gate: its spread across calibration runs
sets its noise band, and only a benchmark whose band is tighter
than the threshold it enforces is armed. A regression verdict
then means something: the new mean sits outside the old mean's
band by more than the threshold, named in both percentages. The
disqualified bench is not deleted, it is reported with its
spread and the two standard repairs, more iterations or a
quieter machine, because noisy benchmarks are usually fixable
and silently dropping them is how coverage rots.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid


@dataclass(frozen=True)
class Bench:
    name: str
    samples: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.samples) < 3:
            raise Invalid(
                f"{self.name} needs at least 3 samples; two "
                "points cannot show a spread"
            )
        if any(sample <= 0 for sample in self.samples):
            raise Invalid(f"{self.name} has nonpositive samples")

    def mean(self) -> float:
        return sum(self.samples) / len(self.samples)

    def spread_percent(self) -> float:
        return 100 * (max(self.samples) - min(self.samples)) / self.mean()


def armed(bench: Bench, threshold_percent: float) -> bool:
    return bench.spread_percent() < threshold_percent


def verdict(
    old: Bench, new: Bench, threshold_percent: float
) -> str:
    if old.name != new.name:
        raise Invalid(
            f"{old.name} and {new.name} are different benchmarks"
        )
    if not armed(old, threshold_percent):
        return (
            f"{old.name} declines to gate: spread "
            f"{old.spread_percent():.1f}% cannot police a "
            f"{threshold_percent:.0f}% threshold; more "
            "iterations or a quieter machine"
        )
    delta_percent = 100 * (new.mean() - old.mean()) / old.mean()
    if delta_percent > threshold_percent:
        return (
            f"REGRESSION {old.name}: {delta_percent:.1f}% over "
            f"a {threshold_percent:.0f}% threshold with "
            f"{old.spread_percent():.1f}% noise; this is signal"
        )
    if delta_percent > 0:
        return (
            f"{old.name}: +{delta_percent:.1f}% is inside the "
            "threshold, not actionable"
        )
    return f"{old.name}: {delta_percent:.1f}%, no regression"


def fleet_report(
    pairs: list[tuple[Bench, Bench]], threshold_percent: float
) -> str:
    if not pairs:
        raise Invalid("no benchmarks to gate")
    lines = []
    gating = 0
    declined = 0
    regressions = 0
    for old, new in pairs:
        line = verdict(old, new, threshold_percent)
        if line.startswith("REGRESSION"):
            regressions += 1
        if "declines to gate" in line:
            declined += 1
        else:
            gating += 1
        lines.append(f"  {line}")
    header = (
        f"{gating} benchmark(s) armed, {declined} declined for "
        f"noise, {regressions} regression(s)"
    )
    return "\n".join([header, *lines])
