"""The build plan: what would run, why, and what it would cost, before running.

The question before a big build is not "will it work" but "how
bad is it", and the plan answers without executing: given the
files that changed, it walks the cone downstream, splits the
targets into will-run and will-hit, prices the will-run column
with per-target costs, and prints the reason beside every entry,
because a plan whose numbers cannot be interrogated is a guess
wearing a table. The refusal to overpromise is structural: the
plan marks targets whose actions read undeclared inputs as
"cost unknown, hermetic hole", since predicting a rebuild
through a hole in the declarations is exactly how plans earn
distrust, and an honest unknown keeps the rest of the table
credible.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid
from forge.graph import Graph


@dataclass
class BuildPlanner:
    graph: Graph
    sources_of: dict[str, tuple[str, ...]]
    cost_of: dict[str, int]
    hermetic_holes: set[str] = field(default_factory=set)

    def _directly_dirty(
        self, changed: set[str]
    ) -> list[str]:
        return sorted(
            name
            for name in self.graph.targets
            if set(self.sources_of.get(name, ())) & changed
        )

    def plan(self, changed_files: tuple[str, ...]) -> str:
        if not changed_files:
            raise Invalid("no changes, no plan; run nothing")
        changed = set(changed_files)
        seeds = self._directly_dirty(changed)
        will_run: dict[str, str] = {}
        for seed in seeds:
            touched = sorted(
                set(self.sources_of.get(seed, ())) & changed
            )
            will_run[seed] = f"reads {', '.join(touched)}"
            for downstream in self.graph.downstream_of(seed):
                will_run.setdefault(
                    downstream, f"downstream of {seed}"
                )
        will_hit = sorted(
            set(self.graph.targets) - set(will_run)
        )
        known_cost = 0
        lines = []
        for name in sorted(will_run):
            if name in self.hermetic_holes:
                lines.append(
                    f"  run {name}: {will_run[name]} "
                    "(cost unknown, hermetic hole)"
                )
                continue
            cost = self.cost_of.get(name)
            if cost is None:
                raise Invalid(f"{name} has no cost on record")
            known_cost += cost
            lines.append(
                f"  run {name}: {will_run[name]} ({cost} ticks)"
            )
        holes = len(
            [n for n in will_run if n in self.hermetic_holes]
        )
        header = (
            f"{len(will_run)} target(s) run, {len(will_hit)} "
            f"hit the cache; {known_cost} tick(s) predicted"
        )
        if holes:
            header += (
                f" plus {holes} unknown(s); an honest unknown "
                "keeps the rest of the table credible"
            )
        return "\n".join([header, *lines])
