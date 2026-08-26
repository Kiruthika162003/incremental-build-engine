"""Graph queries: the questions people actually ask a build graph.

deps answers "what do I need to build this", rdeps answers "what
breaks if I change this", somepath answers "why on earth does the
app depend on the test fixtures", and allpaths counts how tangled
that dependency really is. The path finders return names in walk
order because the person asking is about to read the list out loud
in a code review, and somepath prefers the shortest path since the
review needs one convincing chain, not the complete atlas. Depth
limits exist because "everything within two hops" is the practical
question during an incident; unbounded is just the default, not
the only mode.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Missing
from forge.graph import Graph


@dataclass
class Query:
    graph: Graph

    def deps(self, name: str, depth: int | None = None) -> list[str]:
        self.graph.get(name)
        found: dict[str, int] = {}
        frontier = [(name, 0)]
        while frontier:
            current, hops = frontier.pop(0)
            if depth is not None and hops >= depth:
                continue
            for need in self.graph.get(current).needs:
                if need not in self.graph.targets:
                    continue
                if need not in found or found[need] > hops + 1:
                    found[need] = hops + 1
                    frontier.append((need, hops + 1))
        return sorted(found)

    def rdeps(self, name: str, depth: int | None = None) -> list[str]:
        self.graph.get(name)
        found: dict[str, int] = {}
        frontier = [(name, 0)]
        while frontier:
            current, hops = frontier.pop(0)
            if depth is not None and hops >= depth:
                continue
            for target in self.graph.targets.values():
                if current not in target.needs:
                    continue
                if (
                    target.name not in found
                    or found[target.name] > hops + 1
                ):
                    found[target.name] = hops + 1
                    frontier.append((target.name, hops + 1))
        return sorted(found)

    def somepath(self, start: str, goal: str) -> list[str] | None:
        """The shortest dependency chain from start down to goal."""
        self.graph.get(start)
        self.graph.get(goal)
        frontier = [[start]]
        seen = {start}
        while frontier:
            path = frontier.pop(0)
            if path[-1] == goal:
                return path
            for need in sorted(self.graph.get(path[-1]).needs):
                if need in seen or need not in self.graph.targets:
                    continue
                seen.add(need)
                frontier.append([*path, need])
        return None

    def allpaths(self, start: str, goal: str) -> int:
        self.graph.get(start)
        self.graph.get(goal)
        memo: dict[str, int] = {}

        def count(current: str) -> int:
            if current == goal:
                return 1
            if current in memo:
                return memo[current]
            total = sum(
                count(need)
                for need in self.graph.get(current).needs
                if need in self.graph.targets
            )
            memo[current] = total
            return total

        return count(start)

    def roots(self) -> list[str]:
        needed = {
            need
            for target in self.graph.targets.values()
            for need in target.needs
        }
        return sorted(set(self.graph.targets) - needed)

    def leaves(self) -> list[str]:
        return sorted(
            name
            for name, target in self.graph.targets.items()
            if not target.needs
        )

    def explain_edge(self, start: str, goal: str) -> str:
        path = self.somepath(start, goal)
        if path is None:
            raise Missing(
                f"{start} does not depend on {goal}, by any path"
            )
        count = self.allpaths(start, goal)
        chain = " -> ".join(path)
        return (
            f"{chain} ({count} path{'s' if count != 1 else ''} in total)"
        )
