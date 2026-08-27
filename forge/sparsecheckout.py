"""Sparse checkouts: clone what the graph says, not what the repo has.

A monorepo checkout is a tax paid before the first build starts,
and most of it buys directories this machine will never read.
The planner answers from the graph instead of from habit: given
the targets a developer works on, it walks the dependency
closure, collects the directories those targets actually read,
and emits the sparse profile, always including the build's own
configuration roots because a checkout that cannot load the
graph cannot grow itself later. The savings line compares files
materialized against the full tree, which is the number that
sells the practice, and the failure mode is handled rather than
hoped away: a build that reaches outside its profile names the
missing directory and the one-line profile amendment, because
"file not found" in a sparse tree is a planning bug, not a
mystery.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid, Missing
from forge.graph import Graph

ALWAYS_INCLUDED = ("tools/build",)


def directory_of(path: str) -> str:
    if "/" not in path:
        return "."
    return path.rsplit("/", 1)[0]


@dataclass
class SparsePlanner:
    graph: Graph
    reads_by_target: dict[str, tuple[str, ...]]
    tree_files: dict[str, int]

    def profile(self, wanted: tuple[str, ...]) -> list[str]:
        if not wanted:
            raise Invalid("a sparse profile needs target(s)")
        needed = set(ALWAYS_INCLUDED)
        frontier = list(wanted)
        seen = set()
        while frontier:
            target = frontier.pop()
            if target in seen:
                continue
            seen.add(target)
            if target not in self.graph.targets:
                raise Missing(f"{target} is not in the graph")
            for path in self.reads_by_target.get(target, ()):
                needed.add(directory_of(path))
            frontier.extend(self.graph.get(target).needs)
        return sorted(needed)

    def savings(self, wanted: tuple[str, ...]) -> str:
        chosen = self.profile(wanted)
        materialized = sum(
            count
            for directory, count in self.tree_files.items()
            if directory in chosen
        )
        total = sum(self.tree_files.values())
        if total == 0:
            raise Invalid("the tree has no files to save")
        share = materialized / total
        return (
            f"{len(chosen)} directorie(s), {materialized} of "
            f"{total} files ({share:.0%} of the monorepo)"
        )

    def explain_miss(
        self, wanted: tuple[str, ...], missing_path: str
    ) -> str:
        chosen = self.profile(wanted)
        directory = directory_of(missing_path)
        if directory in chosen:
            return (
                f"{missing_path} is inside the profile; this is "
                "not a sparseness problem"
            )
        return (
            f"{missing_path} lives outside the profile; a build "
            "reaching there undeclared is a planning bug: add "
            f"{directory} to the profile or declare the read"
        )
