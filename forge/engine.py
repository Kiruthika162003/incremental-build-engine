"""The build engine: walk the graph, consult the cache, stop early.

The engine binds targets to actions and builds a goal by walking
the graph in dependency order, asking the cache before running
anything. Early cutoff is the incremental heart: when a dependency
rebuilds but produces byte-identical output, every target above it
sees unchanged input digests, their keys do not move, and the walk
upward becomes a row of cache hits. This is the property that
separates content-addressed builds from timestamp builds, where one
touched file rebuilds the world no matter what came out, and the
build report states it in numbers: targets visited, rules run, hits
taken, and the cutoff count, which is the number of rebuilds the
content model refused to perform.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.actions import Action
from forge.cache import ActionCache
from forge.errors import Invalid, Missing
from forge.graph import Graph
from forge.workspace import Workspace


@dataclass
class BuildReport:
    goal: str
    visited: list[str] = field(default_factory=list)
    ran: list[str] = field(default_factory=list)
    hits: list[str] = field(default_factory=list)
    dirty: list[str] = field(default_factory=list)

    def line(self) -> str:
        return (
            f"{self.goal}: {len(self.visited)} visited, "
            f"{len(self.ran)} ran, {len(self.hits)} from cache"
            + (f", {len(self.dirty)} dirty" if self.dirty else "")
        )


@dataclass
class Engine:
    graph: Graph = field(default_factory=Graph)
    cache: ActionCache = field(default_factory=ActionCache)
    actions: dict[str, Action] = field(default_factory=dict)
    costs: dict[str, int] = field(default_factory=dict)

    def rule(
        self,
        name: str,
        action: Action,
        needs: tuple[str, ...] = (),
        cost: int = 1,
    ) -> None:
        if name in self.actions:
            raise Invalid(f"{name} already has a rule")
        self.graph.declare(name, needs=needs)
        self.actions[name] = action
        self.costs[name] = cost

    def source(self, name: str) -> None:
        """A leaf the workspace provides; nothing builds it."""
        self.graph.declare(name)

    def build(self, goal: str, tree: Workspace) -> BuildReport:
        report = BuildReport(goal=goal)
        for name in self.graph.build_order(goal):
            report.visited.append(name)
            action = self.actions.get(name)
            if action is None:
                if not all(tree.exists(path) for path in [name]):
                    raise Missing(
                        f"source {name} is not in the workspace"
                    )
                continue
            outcome, _ = self.cache.run(
                action, tree, cost=self.costs[name]
            )
            if outcome == "hit":
                report.hits.append(name)
            elif outcome == "miss":
                report.ran.append(name)
            else:
                report.dirty.append(name)
        return report

    def cutoff_count(self, before: BuildReport, after: BuildReport) -> int:
        """Targets that were downstream of a change yet hit the cache."""
        return len(set(after.hits) & set(before.ran))
