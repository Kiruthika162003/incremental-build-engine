"""Output conflicts: one path, one writer, and races named before they run.

Two rules writing the same path is a bug with a random winner, and
the winner changes with the scheduler's mood, which makes it the
worst kind of bug: the one that passes review and fails Tuesdays.
The conflict check is static and total: every declared write is
claimed by exactly one rule or the graph is refused with both
claimants named. The subtler race is temporal: a rule that reads a
path some sibling writes, without declaring the dependency, is
correct or corrupt depending on wave order, so the checker crosses
every rule's reads against every other rule's writes and demands
an edge wherever they intersect. Both checks run before anything
executes, because a race detected by rerunning the build until it
flakes is a race detected by the on-call rotation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.actions import Action
from forge.errors import Invalid
from forge.graph import Graph


@dataclass
class ConflictReport:
    double_writes: list[str] = field(default_factory=list)
    undeclared_races: list[str] = field(default_factory=list)

    def clean(self) -> bool:
        return not self.double_writes and not self.undeclared_races

    def page(self) -> str:
        if self.clean():
            return "no conflicts: one writer per path, every race edged"
        lines = []
        lines.extend(self.double_writes)
        lines.extend(self.undeclared_races)
        return "\n".join(lines)


def check_conflicts(
    graph: Graph, actions: dict[str, Action]
) -> ConflictReport:
    report = ConflictReport()
    writers: dict[str, str] = {}
    for name in sorted(actions):
        for path in actions[name].writes:
            if path in writers:
                report.double_writes.append(
                    f"{path} is written by both {writers[path]} and "
                    f"{name}; the winner would be the scheduler's mood"
                )
            else:
                writers[path] = name
    for name in sorted(actions):
        action = actions[name]
        needs = _transitive_needs(graph, name)
        for path in action.reads:
            producer = writers.get(path)
            if producer is None or producer == name:
                continue
            if producer not in needs:
                report.undeclared_races.append(
                    f"{name} reads {path}, which {producer} writes, "
                    f"with no edge between them; correct or corrupt "
                    f"by wave order"
                )
    return report


def _transitive_needs(graph: Graph, name: str) -> set[str]:
    if name not in graph.targets:
        raise Invalid(f"{name} has an action but no graph target")
    found: set[str] = set()
    frontier = list(graph.get(name).needs)
    while frontier:
        current = frontier.pop()
        if current in found:
            continue
        found.add(current)
        if current in graph.targets:
            frontier.extend(graph.get(current).needs)
    return found


def assert_clean(graph: Graph, actions: dict[str, Action]) -> None:
    report = check_conflicts(graph, actions)
    if not report.clean():
        raise Invalid(report.page())
