"""Aspects: one question asked of every node, answers folded up the graph.

Some questions are not about a target but about everything under
it: which licenses does this binary transitively embed, how many
lines of generated code feed it, does anything below use the
deprecated allocator. An aspect is that question packaged: a
per-node extractor pulls a fact from each target, a folder merges
child answers into the parent's, and the walk runs bottom-up in
dependency order so every node folds exactly once. The result is
a full map, every target annotated with its transitive answer,
computed in one pass rather than one traversal per query, which
is the difference between asking about one binary and asking
about all of them. The license aspect ships as the worked example
because it is the one lawyers actually send.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from forge.errors import Invalid
from forge.graph import Graph


@dataclass
class Aspect:
    name: str
    extract: Callable[[str], frozenset]
    fold: Callable[[frozenset, frozenset], frozenset]

    def walk(self, graph: Graph, goal: str) -> dict[str, frozenset]:
        answers: dict[str, frozenset] = {}
        for target in graph.build_order(goal):
            own = self.extract(target)
            if not isinstance(own, frozenset):
                raise Invalid(
                    f"{self.name}: the extractor must return a "
                    f"frozenset, got {type(own).__name__}"
                )
            folded = own
            for need in graph.get(target).needs:
                folded = self.fold(folded, answers[need])
            answers[target] = folded
        return answers


def union_fold(left: frozenset, right: frozenset) -> frozenset:
    return left | right


def license_aspect(
    declared: dict[str, str],
) -> Aspect:
    def extract(target: str) -> frozenset:
        held = declared.get(target)
        return frozenset([held]) if held else frozenset()

    return Aspect(
        name="licenses", extract=extract, fold=union_fold
    )


FORBIDDEN_TOGETHER = frozenset({"GPL-3.0", "proprietary"})


def license_verdict(
    answers: dict[str, frozenset], goal: str
) -> str:
    held = answers[goal]
    if held >= FORBIDDEN_TOGETHER:
        return (
            f"{goal}: REFUSED, {sorted(FORBIDDEN_TOGETHER)} cannot "
            f"ship in one artifact"
        )
    return (
        f"{goal}: ships {sorted(held) if held else 'nothing declared'}"
    )
