"""Test selection: run what the change can reach, prove the rest safe.

Running every test on every change is a tax that grows with the
repository, and skipping tests by directory naming is a bet that
loses eventually. The selector is neither: a test target's verdict
can only change if something it transitively depends on changed,
so the tests worth running are exactly the changed files' reverse
cone intersected with the test set, and everything outside that
intersection is provably unaffected, not probably. The proof
obligation runs in both directions: the selector also reports any
test with no path to any source at all, because a test depending
on nothing is either misdeclared or testing the weather, and both
deserve a human. The savings line divides skipped by total since
that ratio is the tax refund, and it grows exactly as fast as the
repository does, which is the entire economic argument.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Missing
from forge.graph import Graph
from forge.query import Query


@dataclass
class Selection:
    changed: list[str]
    selected: list[str]
    skipped: list[str]
    orphans: list[str] = field(default_factory=list)

    def refund(self) -> float:
        total = len(self.selected) + len(self.skipped)
        return len(self.skipped) / total if total else 0.0

    def line(self) -> str:
        return (
            f"{len(self.changed)} changed: run {len(self.selected)}, "
            f"skip {len(self.skipped)} ({self.refund():.0%} refund)"
        )


@dataclass
class Selector:
    graph: Graph
    test_targets: set[str] = field(default_factory=set)

    def mark_test(self, name: str) -> None:
        self.graph.get(name)
        self.test_targets.add(name)

    def orphan_tests(self) -> list[str]:
        query = Query(graph=self.graph)
        leaves = set(query.leaves())
        orphans = []
        for name in sorted(self.test_targets):
            deps = query.deps(name)
            if not any(dep in leaves for dep in deps):
                orphans.append(name)
        return orphans

    def select(self, changed: list[str]) -> Selection:
        for name in changed:
            if name not in self.graph.targets:
                raise Missing(
                    f"{name} changed but the graph has never heard of it"
                )
        query = Query(graph=self.graph)
        reached: set[str] = set()
        for name in changed:
            reached.update(query.rdeps(name))
            reached.add(name)
        selected = sorted(self.test_targets & reached)
        skipped = sorted(self.test_targets - reached)
        return Selection(
            changed=sorted(changed),
            selected=selected,
            skipped=skipped,
            orphans=self.orphan_tests(),
        )
