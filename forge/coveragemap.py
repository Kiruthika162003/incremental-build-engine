"""Coverage per target: the untested list is the deliverable.

A single repository-wide coverage percentage is a number to feel
things about; per-target coverage is a work list. The map joins
what each test exercises against what each target contains, and
the three outputs are the ones a team can act on: targets no test
touches at all, sorted by their blast radius because the untested
thing everyone depends on outranks the untested leaf; targets
whose coverage fell since the last snapshot, with both numbers;
and the coverage a proposed test deletion would orphan, answered
before the deletion lands rather than in the postmortem of the
bug it would have caught. The gate is per target, not global,
since a global gate lets a well-tested corner subsidise an
untested core forever.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid, Missing
from forge.graph import Graph
from forge.query import Query


@dataclass
class CoverageMap:
    graph: Graph
    exercised_by: dict[str, set[str]] = field(default_factory=dict)
    snapshot_pct: dict[str, int] = field(default_factory=dict)
    coverage_pct: dict[str, int] = field(default_factory=dict)

    def record(
        self, test: str, targets: set[str], pct: dict[str, int]
    ) -> None:
        for target in targets:
            self.graph.get(target)
            self.exercised_by.setdefault(target, set()).add(test)
        for target, value in pct.items():
            if not 0 <= value <= 100:
                raise Invalid("coverage is a percentage")
            self.coverage_pct[target] = max(
                self.coverage_pct.get(target, 0), value
            )

    def untested(self, all_targets: list[str]) -> list[str]:
        query = Query(graph=self.graph)
        bare = [
            target
            for target in all_targets
            if target not in self.exercised_by
        ]
        return sorted(
            bare,
            key=lambda target: (
                -len(query.rdeps(target)),
                target,
            ),
        )

    def snapshot(self) -> None:
        self.snapshot_pct = dict(self.coverage_pct)

    def fell_since_snapshot(self) -> list[str]:
        if not self.snapshot_pct:
            raise Invalid("no snapshot to compare against")
        fallen = []
        for target in sorted(self.snapshot_pct):
            then = self.snapshot_pct[target]
            now = self.coverage_pct.get(target, 0)
            if now < then:
                fallen.append(
                    f"{target}: {then}% -> {now}%"
                )
        return fallen

    def deletion_orphans(self, test: str) -> list[str]:
        found = sorted(
            target
            for target, tests in self.exercised_by.items()
            if tests == {test}
        )
        if not any(
            test in tests for tests in self.exercised_by.values()
        ):
            raise Missing(f"{test} exercises nothing on record")
        return found

    def gate(self, target: str, floor: int) -> str:
        held = self.coverage_pct.get(target, 0)
        if held < floor:
            return (
                f"REFUSED: {target} at {held}% against a floor of "
                f"{floor}%; a global gate would have let this slide"
            )
        return f"{target} at {held}% clears its {floor}% floor"
