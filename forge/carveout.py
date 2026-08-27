"""Carving a team out of the monorepo: the boundary is a list of edges.

Extracting a package set into its own repository is decided in
meetings and executed against edges, and the meetings go better
when the edges arrive first. The planner takes the proposed
carve set and names the boundary in both directions: outbound
edges are dependencies the carved repo will need published,
vendored, or pinned, and inbound edges are consumers who will
need the carved code as a versioned dependency, which is the
side teams forget because it is other people's work. The
verdict is arithmetic, not sentiment: a carve with a package
cycle across the boundary is refused outright since the two
repos could never build first, and the effort score weighs both
edge lists, because a clean outbound story with forty inbound
consumers is not a carve, it is a migration program wearing a
carve's clothes.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid
from forge.graph import Graph
from forge.visibility import package_of


@dataclass
class CarvePlan:
    graph: Graph
    carve_packages: set[str]

    def __post_init__(self) -> None:
        if not self.carve_packages:
            raise Invalid("a carve of nothing carves nothing")

    def _side(self, target: str) -> str:
        return (
            "carved"
            if package_of(target) in self.carve_packages
            else "staying"
        )

    def outbound(self) -> list[str]:
        found = []
        for name in sorted(self.graph.targets):
            if self._side(name) != "carved":
                continue
            for need in sorted(self.graph.get(name).needs):
                if (
                    need in self.graph.targets
                    and self._side(need) == "staying"
                ):
                    found.append(f"{name} -> {need}")
        return found

    def inbound(self) -> list[str]:
        found = []
        for name in sorted(self.graph.targets):
            if self._side(name) != "staying":
                continue
            for need in sorted(self.graph.get(name).needs):
                if (
                    need in self.graph.targets
                    and self._side(need) == "carved"
                ):
                    found.append(f"{name} -> {need}")
        return found

    def verdict(self) -> str:
        out_edges = self.outbound()
        in_edges = self.inbound()
        if out_edges and in_edges:
            out_packages = {
                package_of(edge.split(" -> ")[1])
                for edge in out_edges
            }
            in_sources = {
                package_of(edge.split(" -> ")[0])
                for edge in in_edges
            }
            if out_packages & in_sources:
                crossing = sorted(out_packages & in_sources)
                return (
                    f"REFUSED: {', '.join(crossing)} sits on "
                    "both sides of the boundary; neither repo "
                    "could ever build first"
                )
        effort = len(out_edges) + 3 * len(in_edges)
        lines = [
            f"carve {'/'.join(sorted(self.carve_packages))}: "
            f"{len(out_edges)} outbound, {len(in_edges)} "
            f"inbound, effort {effort}"
        ]
        lines.extend(
            f"  outbound (publish or pin): {edge}"
            for edge in out_edges
        )
        lines.extend(
            f"  inbound (their migration, your calendar): "
            f"{edge}"
            for edge in in_edges
        )
        if len(in_edges) > 10:
            lines.append(
                "  verdict: a migration program wearing a "
                "carve's clothes"
            )
        return "\n".join(lines)
