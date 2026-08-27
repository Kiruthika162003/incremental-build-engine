"""Unused dependencies: the edge nobody walks still bills everyone.

A declared need that the rule never reads is not harmless
paperwork: it widens the rebuild cone, since every change to the
unused dependency rebuilds this target for nothing, and it widens
the blast radius the reviewers reason about. The pruner crosses
declarations against observations from real runs: an edge is
suspect when the target's action read nothing the dependency
produces, and the report prices each suspect edge in wasted
rebuilds, the count of times this target rebuilt for a change it
never consumed. Pruning is advice, never automatic, because a
dependency can be load-bearing without being read, an ordering
constraint or a test harness, so the report distinguishes "never
read, never rebuilt for" from "never read, rebuilt for twelve
times", and only the second one is worth a meeting.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.actions import Action
from forge.errors import Invalid
from forge.graph import Graph


@dataclass
class PruneCandidate:
    target: str
    unused_need: str
    wasted_rebuilds: int

    def line(self) -> str:
        if self.wasted_rebuilds == 0:
            return (
                f"{self.target} -> {self.unused_need}: never read, "
                f"never billed; maybe an ordering constraint"
            )
        return (
            f"{self.target} -> {self.unused_need}: never read, "
            f"rebuilt {self.wasted_rebuilds} times for it; "
            f"worth a meeting"
        )


@dataclass
class Pruner:
    graph: Graph
    actions: dict[str, Action]
    observed_reads: dict[str, set[str]] = field(default_factory=dict)
    rebuild_causes: dict[tuple[str, str], int] = field(
        default_factory=dict
    )

    def observe_run(self, target: str, read: set[str]) -> None:
        if target not in self.actions:
            raise Invalid(f"{target} has no action to observe")
        self.observed_reads.setdefault(target, set()).update(read)

    def record_rebuild(self, target: str, because_of: str) -> None:
        key = (target, because_of)
        self.rebuild_causes[key] = self.rebuild_causes.get(key, 0) + 1

    def _produces(self, need: str) -> set[str]:
        action = self.actions.get(need)
        if action is None:
            return {need}
        return set(action.writes)

    def candidates(self) -> list[PruneCandidate]:
        found = []
        for target in sorted(self.actions):
            reads = self.observed_reads.get(target)
            if reads is None:
                continue
            for need in sorted(self.graph.get(target).needs):
                produced = self._produces(need)
                if produced & reads:
                    continue
                found.append(
                    PruneCandidate(
                        target=target,
                        unused_need=need,
                        wasted_rebuilds=self.rebuild_causes.get(
                            (target, need), 0
                        ),
                    )
                )
        return sorted(
            found,
            key=lambda candidate: (
                -candidate.wasted_rebuilds,
                candidate.target,
            ),
        )

    def report(self) -> str:
        found = self.candidates()
        if not found:
            return "no unused dependencies observed"
        lines = [candidate.line() for candidate in found]
        billed = sum(
            candidate.wasted_rebuilds for candidate in found
        )
        lines.append(
            f"{len(found)} suspect edges, {billed} wasted rebuilds"
        )
        return "\n".join(lines)
