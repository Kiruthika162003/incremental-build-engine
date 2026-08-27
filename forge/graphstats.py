"""Graph shape metrics: the numbers that predict how a build will feel.

Two graphs with a thousand targets each can build like a sprint
or a queue, and the difference is shape: depth bounds the
critical path no matter how many workers arrive, fan-in marks the
bottleneck targets everything funnels through, and fan-out marks
the explosive ones whose change rebuilds a county. The stats page
computes all three with their extremes named, because a
percentile without the name of the offender is trivia, and the
shape verdict compresses the profile into the sentence a new
engineer needs on day one: this build is deep and narrow, wide
and shallow, or funnelled through three chokepoints that deserve
their own on-call. The chokepoint list doubles as the review
gate's watch list, since an edit to a high-fan-in target deserves
more eyes by arithmetic, not by folklore.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid
from forge.graph import Graph

CHOKEPOINT_FANIN = 3


@dataclass
class GraphStats:
    graph: Graph

    def depth(self) -> int:
        depths: dict[str, int] = {}
        for name in self._order_all():
            needs = [
                need
                for need in self.graph.get(name).needs
                if need in self.graph.targets
            ]
            depths[name] = (
                0
                if not needs
                else 1 + max(depths[need] for need in needs)
            )
        return max(depths.values()) if depths else 0

    def _order_all(self) -> list[str]:
        ordered: list[str] = []
        placed: set[str] = set()

        def visit(name: str) -> None:
            if name in placed:
                return
            for need in sorted(self.graph.get(name).needs):
                if need in self.graph.targets:
                    visit(need)
            placed.add(name)
            ordered.append(name)

        for name in sorted(self.graph.targets):
            visit(name)
        return ordered

    def fan_in(self) -> dict[str, int]:
        counts = dict.fromkeys(self.graph.targets, 0)
        for target in self.graph.targets.values():
            for need in target.needs:
                if need in counts:
                    counts[need] += 1
        return counts

    def fan_out(self) -> dict[str, int]:
        return {
            name: len(
                [
                    need
                    for need in target.needs
                    if need in self.graph.targets
                ]
            )
            for name, target in self.graph.targets.items()
        }

    def chokepoints(self) -> list[tuple[str, int]]:
        return sorted(
            (
                (name, count)
                for name, count in self.fan_in().items()
                if count >= CHOKEPOINT_FANIN
            ),
            key=lambda row: (-row[1], row[0]),
        )

    def shape_verdict(self) -> str:
        if not self.graph.targets:
            raise Invalid("an empty graph has no shape")
        depth = self.depth()
        width = len(self.graph.targets) / max(depth, 1)
        chokes = self.chokepoints()
        if chokes:
            names = ", ".join(name for name, _ in chokes[:3])
            return (
                f"funnelled: {len(chokes)} chokepoint(s), edits to "
                f"{names} deserve more eyes by arithmetic"
            )
        if depth > width:
            return (
                f"deep and narrow (depth {depth}): workers will "
                f"idle, the chain is the ceiling"
            )
        return (
            f"wide and shallow (depth {depth}): parallelism will "
            f"pay here"
        )
