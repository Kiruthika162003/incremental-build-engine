"""Action batching: a hundred tiny actions, one process, honest keys.

Spawning a process per action has a floor cost, and a build made
of a thousand two-tick lints spends more on floors than on work.
Batching amortises the floor: compatible actions, same tool, no
edges between them, run as one invocation, and the spawn floor is
paid once per batch instead of once per action. The honesty
problem is the cache: a batch has one exit but many results, and
caching the batch under one key means one changed input re-runs a
hundred innocents. So the batch is an execution strategy, never a
cache identity: each member keeps its own action key and its own
cache entry, the batch merely carries them to the processor
together, and the savings line reports floors avoided while the
hit rate stays per-action, which is the only arrangement where
batching is free instead of a trade.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.actions import Action
from forge.cache import ActionCache
from forge.errors import Invalid
from forge.graph import Graph
from forge.workspace import Workspace

SPAWN_FLOOR = 3


@dataclass
class BatchPlan:
    batches: list[list[str]] = field(default_factory=list)

    def floors_paid(self) -> int:
        return len(self.batches) * SPAWN_FLOOR

    def floors_avoided(self) -> int:
        members = sum(len(batch) for batch in self.batches)
        return members * SPAWN_FLOOR - self.floors_paid()


def plan_batches(
    graph: Graph,
    actions: dict[str, Action],
    goal: str,
    batch_limit: int = 10,
) -> BatchPlan:
    if batch_limit <= 0:
        raise Invalid("the batch limit must be positive")
    plan = BatchPlan()
    for wave in graph.waves(goal):
        by_tool: dict[str, list[str]] = {}
        for name in wave:
            action = actions.get(name)
            if action is None:
                continue
            tool = action.command.split()[0]
            by_tool.setdefault(tool, []).append(name)
        for tool in sorted(by_tool):
            members = by_tool[tool]
            for start in range(0, len(members), batch_limit):
                plan.batches.append(
                    members[start : start + batch_limit]
                )
    return plan


@dataclass
class BatchRunner:
    cache: ActionCache = field(default_factory=ActionCache)
    spawns: int = 0

    def run_batch(
        self,
        batch: list[str],
        actions: dict[str, Action],
        tree: Workspace,
    ) -> dict[str, str]:
        outcomes = {}
        spawned = False
        for name in batch:
            outcome, _ = self.cache.run(actions[name], tree)
            outcomes[name] = outcome
            if outcome != "hit" and not spawned:
                self.spawns += 1
                spawned = True
        return outcomes

    def savings(self, plan: BatchPlan) -> str:
        return (
            f"{self.spawns} spawns for "
            f"{sum(len(batch) for batch in plan.batches)} actions; "
            f"{plan.floors_avoided()} floor ticks avoided"
        )
