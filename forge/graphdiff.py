"""Graph diffing: the review sees what the build will do differently.

A change to BUILD files is a change to the machine that builds
everything else, and reviewing it as text misses what matters: the
edges. The diff compares two graphs and reports in the language of
consequences: targets added and removed, edges rewired with both
endpoints named, and the cache impact, which existing targets will
miss on their next build because their dependency set changed even
though no source did. The impact walk is the piece reviewers
cannot do in their heads: a rewired edge invalidates its target
and everything downstream, and the diff prints that closure with a
count, because approving a two-line BUILD change that quietly
rebuilds four thousand targets should at least be done knowingly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.graph import Graph


@dataclass
class GraphDelta:
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    edges_gained: list[tuple[str, str]] = field(default_factory=list)
    edges_lost: list[tuple[str, str]] = field(default_factory=list)

    def rewired_targets(self) -> list[str]:
        touched = {target for target, _ in self.edges_gained}
        touched.update(target for target, _ in self.edges_lost)
        return sorted(touched)

    def quiet(self) -> bool:
        return not (
            self.added
            or self.removed
            or self.edges_gained
            or self.edges_lost
        )


def diff(before: Graph, after: Graph) -> GraphDelta:
    delta = GraphDelta()
    old_names = set(before.targets)
    new_names = set(after.targets)
    delta.added = sorted(new_names - old_names)
    delta.removed = sorted(old_names - new_names)
    for name in sorted(old_names & new_names):
        old_needs = set(before.get(name).needs)
        new_needs = set(after.get(name).needs)
        for need in sorted(new_needs - old_needs):
            delta.edges_gained.append((name, need))
        for need in sorted(old_needs - new_needs):
            delta.edges_lost.append((name, need))
    return delta


def cache_impact(after: Graph, delta: GraphDelta) -> list[str]:
    """Existing targets that will miss although no source changed."""
    seeds = [
        name
        for name in delta.rewired_targets()
        if name in after.targets
    ]
    hit: set[str] = set(seeds)
    for name in seeds:
        hit.update(
            target
            for target in after.downstream_of(name)
        )
    return sorted(hit)


def review_page(before: Graph, after: Graph) -> str:
    delta = diff(before, after)
    if delta.quiet():
        return "no structural change: the graphs are the same shape"
    lines = []
    if delta.added:
        lines.append(f"added: {', '.join(delta.added)}")
    if delta.removed:
        lines.append(f"removed: {', '.join(delta.removed)}")
    for target, need in delta.edges_gained:
        lines.append(f"edge gained: {target} -> {need}")
    for target, need in delta.edges_lost:
        lines.append(f"edge lost: {target} -> {need}")
    impact = cache_impact(after, delta)
    if impact:
        lines.append(
            f"cache impact: {len(impact)} existing targets will miss "
            f"({', '.join(impact)})"
        )
    return "\n".join(lines)
