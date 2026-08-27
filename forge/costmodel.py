"""The cost model: durations are learned, decayed, and never invented.

The scheduler, the profiler, and the warmer all consume per-rule
costs, and a checked-in table drifts from reality one deploy at a
time. The model learns instead: every completed action reports its
duration, the estimate is an exponentially decayed blend so last
week's compiler upgrade outweighs last year's, and rules never run
inherit the median of their tool's family rather than a magic
constant, because a brand-new proto rule behaves like the other
proto rules, not like the number three. Confidence travels with
every estimate: rules with one observation say so, and the
consumers can decide whether a low-confidence number should widen
a shard or merely annotate it. The drift report names rules whose
recent runs left their own estimate's neighbourhood, which is the
early warning that someone made a fast rule slow.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

BLEND = 0.3
DRIFT_FACTOR = 2.0


@dataclass
class CostEntry:
    tool: str
    estimate: float
    observations: int = 0


@dataclass
class CostModel:
    entries: dict[str, CostEntry] = field(default_factory=dict)

    def observe(self, rule: str, tool: str, duration: int) -> None:
        if duration < 0:
            raise Invalid("durations cannot be negative")
        held = self.entries.get(rule)
        if held is None:
            self.entries[rule] = CostEntry(
                tool=tool, estimate=float(duration), observations=1
            )
            return
        held.estimate = round(
            (1 - BLEND) * held.estimate + BLEND * duration, 2
        )
        held.observations += 1

    def _family_median(self, tool: str) -> float | None:
        family = sorted(
            entry.estimate
            for entry in self.entries.values()
            if entry.tool == tool and entry.observations > 0
        )
        if not family:
            return None
        middle = len(family) // 2
        if len(family) % 2:
            return family[middle]
        return (family[middle - 1] + family[middle]) / 2

    def estimate(self, rule: str, tool: str) -> tuple[float, str]:
        held = self.entries.get(rule)
        if held is not None:
            confidence = (
                "single observation"
                if held.observations == 1
                else f"{held.observations} observations"
            )
            return held.estimate, confidence
        inherited = self._family_median(tool)
        if inherited is None:
            raise Invalid(
                f"no history for {rule} and no {tool} family to "
                f"inherit from; run it once before planning around it"
            )
        return inherited, f"inherited from the {tool} family"

    def drift_report(self, recent: dict[str, int]) -> list[str]:
        drifted = []
        for rule in sorted(recent):
            held = self.entries.get(rule)
            if held is None or held.estimate == 0:
                continue
            ratio = recent[rule] / held.estimate
            if ratio >= DRIFT_FACTOR or ratio <= 1 / DRIFT_FACTOR:
                drifted.append(
                    f"{rule}: estimated {held.estimate}, ran "
                    f"{recent[rule]}; someone made a "
                    f"{'fast rule slow' if ratio > 1 else 'slow rule fast'}"
                )
        return drifted
