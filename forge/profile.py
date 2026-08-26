"""The build profile: where the ticks went, and which ticks were the path.

A build's timeline answers two different complaints with one data
set. "The build is slow" is about total ticks, and the hotspot
table sorts rules by cost so the fattest target is the first line.
"The build got slower" is about the critical path, and a rule off
the path can triple in cost without moving wall clock at all,
which is why optimising the hotspot table's top line is so often a
week wasted: the path table shows each rule's slack, the ticks it
could grow before it touches the path, and the honest advice is
printed with the numbers: optimise the zero-slack rules, ignore
the rest until the path moves. Both tables come from one
simulation so they can never disagree about what happened.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid
from forge.graph import Graph
from forge.scheduler import Scheduler


@dataclass(frozen=True)
class PathRow:
    target: str
    cost: int
    slack: int

    def line(self) -> str:
        mark = "  <- the path" if self.slack == 0 else ""
        return f"{self.target}: cost {self.cost}, slack {self.slack}{mark}"


@dataclass
class Profile:
    graph: Graph
    costs: dict[str, int]

    def _scheduler(self) -> Scheduler:
        return Scheduler(graph=self.graph, costs=self.costs)

    def hotspots(self, goal: str, top: int = 5) -> list[tuple[str, int]]:
        order = self.graph.build_order(goal)
        rows = sorted(
            ((name, self.costs.get(name, 0)) for name in order),
            key=lambda row: (-row[1], row[0]),
        )
        return rows[:top]

    def slack_table(self, goal: str) -> list[PathRow]:
        scheduler = self._scheduler()
        finish: dict[str, int] = {}
        order = self.graph.build_order(goal)
        for name in order:
            needs = self.graph.get(name).needs
            base = max(
                (finish[need] for need in needs if need in finish),
                default=0,
            )
            finish[name] = base + self.costs.get(name, 0)
        makespan, _ = scheduler.critical_path(goal)
        latest: dict[str, int] = {goal: makespan}
        for name in reversed(order):
            if name not in latest:
                latest[name] = min(
                    (
                        latest[user] - self.costs.get(user, 0)
                        for user in order
                        if name in self.graph.get(user).needs
                        and user in latest
                    ),
                    default=makespan,
                )
        rows = []
        for name in order:
            slack = latest[name] - finish[name]
            if slack < 0:
                raise Invalid(f"negative slack on {name}: the math broke")
            rows.append(
                PathRow(
                    target=name,
                    cost=self.costs.get(name, 0),
                    slack=slack,
                )
            )
        return sorted(rows, key=lambda row: (row.slack, -row.cost, row.target))

    def advice(self, goal: str) -> str:
        rows = self.slack_table(goal)
        zero = {row.target for row in rows if row.slack == 0}
        on_path = [
            name
            for name in self.graph.build_order(goal)
            if name in zero
        ]
        fattest = self.hotspots(goal, top=1)[0]
        if fattest[0] in on_path:
            return (
                f"optimise {fattest[0]}: it is both the fattest rule "
                f"and on the path"
            )
        return (
            f"the fattest rule ({fattest[0]}, {fattest[1]} ticks) is "
            f"OFF the path; optimising it moves nothing. The path runs "
            f"through {', '.join(on_path)}"
        )

    def page(self, goal: str) -> str:
        lines = ["hotspots:"]
        for name, cost in self.hotspots(goal):
            lines.append(f"  {name}: {cost}")
        lines.append("slack:")
        for row in self.slack_table(goal):
            lines.append(f"  {row.line()}")
        lines.append(self.advice(goal))
        return "\n".join(lines)
