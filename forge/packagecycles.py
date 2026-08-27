"""Package cycles: legal at the target level, a debt at the package level.

The target graph refuses cycles outright, but two packages can
depend on each other through disjoint targets, auth needing a
billing helper while billing needs an auth type, and every such
package cycle is a future refactor held hostage: neither package
can be extracted, versioned, or owned cleanly while the loop
stands. The detector lifts the target graph to a package graph,
finds the strongly connected components, and reports each
nontrivial component with the specific target edges that close
it, because breaking a package cycle means moving one of those
edges and the list is the menu. The trend is the governance:
cycles are counted per audit and the number is only allowed to
fall, a ratchet, since teams that cannot fix old cycles can at
least be stopped from minting new ones.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid
from forge.graph import Graph
from forge.visibility import package_of


@dataclass
class PackageCycleAuditor:
    graph: Graph
    last_count: int | None = None

    def _package_edges(self) -> dict[str, set[str]]:
        edges: dict[str, set[str]] = {}
        for target in self.graph.targets.values():
            source_package = package_of(target.name)
            for need in target.needs:
                if need not in self.graph.targets:
                    continue
                need_package = package_of(need)
                if source_package != need_package:
                    edges.setdefault(source_package, set()).add(
                        need_package
                    )
        return edges

    def _components(self) -> list[set[str]]:
        edges = self._package_edges()
        packages = set(edges)
        for targets in edges.values():
            packages.update(targets)
        components = []
        remaining = set(packages)
        while remaining:
            start = min(remaining)
            forward = self._reachable(start, edges)
            backward = {
                package
                for package in packages
                if start in self._reachable(package, edges)
            }
            component = forward & backward
            component.add(start)
            if len(component) > 1:
                components.append(component)
            remaining -= component
        return components

    def _reachable(
        self, start: str, edges: dict[str, set[str]]
    ) -> set[str]:
        seen: set[str] = set()
        frontier = [start]
        while frontier:
            current = frontier.pop()
            for nxt in edges.get(current, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    frontier.append(nxt)
        return seen

    def closing_edges(self, component: set[str]) -> list[str]:
        found = []
        for target in sorted(self.graph.targets):
            source_package = package_of(target)
            if source_package not in component:
                continue
            for need in sorted(self.graph.get(target).needs):
                if need not in self.graph.targets:
                    continue
                need_package = package_of(need)
                if (
                    need_package in component
                    and need_package != source_package
                ):
                    found.append(f"{target} -> {need}")
        return found

    def audit(self) -> str:
        components = self._components()
        count = len(components)
        ratchet = ""
        if self.last_count is not None and count > self.last_count:
            raise Invalid(
                f"the cycle count rose from {self.last_count} to "
                f"{count}; the ratchet only turns one way"
            )
        self.last_count = count
        if not components:
            return "no package cycles; every package can leave home"
        lines = [f"{count} package cycle(s){ratchet}"]
        for component in sorted(
            components, key=lambda c: sorted(c)[0]
        ):
            lines.append(f"  loop: {', '.join(sorted(component))}")
            for edge in self.closing_edges(component):
                lines.append(f"    {edge}")
        return "\n".join(lines)
