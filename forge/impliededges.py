"""Transitive reduction: the edge the graph already implies is noise.

When app needs core and util, and util itself needs core, the
app-to-core edge changes nothing about build order, correctness,
or the cone of any rebuild; it is a sentence the graph already
said, restated in a BUILD file where it will now rot. The
reducer finds every edge whose endpoints are already connected
through the remaining graph and names it removable, with the
witness path that makes it redundant, because a deletion
recommendation without its proof reads as an opinion. The
counterweight is stated with the same care: a redundant edge
being removable does not make removing it free of meaning, since
teams sometimes keep a direct edge as a declared contract that
the transitive route might not honor forever, so the report
recommends, records the witness, and leaves the deletion to a
person who knows why the edge was written.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid
from forge.graph import Graph


@dataclass
class EdgeReducer:
    graph: Graph

    def _reachable_avoiding(
        self, start: str, goal: str, skip_edge: tuple[str, str]
    ) -> list[str] | None:
        trail = {start: [start]}
        frontier = [start]
        while frontier:
            current = frontier.pop(0)
            if current == goal:
                return trail[current]
            for need in sorted(self.graph.get(current).needs):
                if (current, need) == skip_edge:
                    continue
                if need in self.graph.targets and need not in trail:
                    trail[need] = trail[current] + [need]
                    frontier.append(need)
        return None

    def redundant_edges(self) -> list[tuple[str, str, str]]:
        found = []
        for name in sorted(self.graph.targets):
            for need in sorted(self.graph.get(name).needs):
                if need not in self.graph.targets:
                    continue
                witness = self._reachable_avoiding(
                    name, need, skip_edge=(name, need)
                )
                if witness is not None:
                    found.append(
                        (name, need, " -> ".join(witness))
                    )
        return found

    def report(self) -> str:
        if not self.graph.targets:
            raise Invalid("an empty graph implies nothing")
        redundant = self.redundant_edges()
        total_edges = sum(
            1
            for name in self.graph.targets
            for need in self.graph.get(name).needs
            if need in self.graph.targets
        )
        if not redundant:
            return (
                f"{total_edges} edge(s), none implied; every "
                "declaration is load-bearing"
            )
        lines = [
            f"{len(redundant)} of {total_edges} edge(s) are "
            "already implied"
        ]
        for name, need, witness in redundant:
            lines.append(
                f"  {name} -> {need} is restated by {witness}; "
                "removable, but only a person knows if it was "
                "a contract"
            )
        return "\n".join(lines)
