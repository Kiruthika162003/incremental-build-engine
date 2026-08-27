"""Cache warming: tonight's idle machines buy tomorrow's first build.

The morning's first build misses on everything yesterday's merges
touched, and the farm sat idle all night. The warmer spends the
idle hours building what the morning will ask for, and its skill
is the prediction: the seed is the day's merged changes, the
predicted keys are their downstream cones, and the budget bounds
how much night there is. Prediction quality is measured, not
assumed: the morning's actual requests are scored against the
prewarmed set, and the two failure modes are priced separately,
cold requests the warmer should have seen, and wasted warmth built
for nobody. A warmer with high waste is guessing; one with high
cold is timid; and the score line prints both because the fix for
each is opposite, and tuning the budget against the wrong failure
buys more of it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid
from forge.graph import Graph


@dataclass
class WarmPlan:
    predicted: list[str]
    budget_used: int


@dataclass
class Warmer:
    graph: Graph
    costs: dict[str, int]

    def plan(
        self, merged_changes: list[str], budget: int
    ) -> WarmPlan:
        if budget <= 0:
            raise Invalid("a warmer needs some night to work with")
        cone: set[str] = set()
        for change in merged_changes:
            if change not in self.graph.targets:
                raise Invalid(
                    f"{change} merged but the graph never heard of it"
                )
            cone.update(self.graph.downstream_of(change))
        ranked = sorted(
            cone,
            key=lambda name: (-self.costs.get(name, 0), name),
        )
        chosen = []
        spent = 0
        for name in ranked:
            cost = self.costs.get(name, 0)
            if spent + cost > budget:
                continue
            chosen.append(name)
            spent += cost
        return WarmPlan(predicted=sorted(chosen), budget_used=spent)


@dataclass
class MorningScore:
    warmed: set[str]
    requested: set[str] = field(default_factory=set)

    def request(self, name: str) -> str:
        self.requested.add(name)
        return "warm" if name in self.warmed else "cold"

    def cold_misses(self) -> list[str]:
        return sorted(self.requested - self.warmed)

    def wasted_warmth(self) -> list[str]:
        return sorted(self.warmed - self.requested)

    def line(self) -> str:
        hits = len(self.requested & self.warmed)
        return (
            f"{hits} warm, {len(self.cold_misses())} cold "
            f"(timidity), {len(self.wasted_warmth())} wasted "
            f"(guessing)"
        )

    def diagnosis(self) -> str:
        cold = len(self.cold_misses())
        waste = len(self.wasted_warmth())
        if cold == 0 and waste == 0:
            return "the prediction was exact; do not touch it"
        if cold > waste:
            return "timid: raise the budget or widen the cone"
        if waste > cold:
            return "guessing: narrow the cone before raising anything"
        return "balanced failures; tune with care, the fixes oppose"
