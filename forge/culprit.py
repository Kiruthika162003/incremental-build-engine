"""Culprit finding: the red build names one commit, by arithmetic.

A batch of commits lands, the build goes red, and the wrong ritual
begins: everyone whose change is in the window explains themselves
in a thread. Bisection replaces the thread with log-two-of-n
builds: test the midpoint, keep the half that turns red, and the
culprit falls out with its name attached, no confession required.
The bisector assumes what bisection must, that the predicate flips
once and stays flipped; a flaky predicate breaks the assumption,
so every verdict is optionally sampled twice and a disagreement
aborts the hunt with "the test is flaky" instead of convicting an
innocent commit, which matters because a bisection that lies does
so with total confidence. The receipt counts builds spent against
the batch size, since seven builds instead of a hundred and
twenty-eight is the number that justifies the machinery.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class Hunt:
    commits: list[str]
    is_broken_at: Callable[[str], bool]
    double_check: bool = False
    builds_spent: int = 0
    verdicts: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.commits) < 2:
            raise Invalid("a hunt needs a window of at least two commits")

    def _probe(self, commit: str) -> bool:
        first = self.is_broken_at(commit)
        self.builds_spent += 1
        if self.double_check:
            second = self.is_broken_at(commit)
            self.builds_spent += 1
            if first != second:
                raise Invalid(
                    f"the test is flaky: {commit} answered both ways; "
                    f"no conviction"
                )
        self.verdicts.append(
            f"{commit}: {'red' if first else 'green'}"
        )
        return first

    def run(self) -> str:
        if not self._probe(self.commits[-1]):
            raise Invalid(
                "the window's end is green; there is nothing to hunt"
            )
        if self._probe(self.commits[0]):
            raise Invalid(
                "the window's start is already red; widen the window"
            )
        low = 0
        high = len(self.commits) - 1
        while high - low > 1:
            middle = (low + high) // 2
            if self._probe(self.commits[middle]):
                high = middle
            else:
                low = middle
        return self.commits[high]

    def receipt(self, culprit: str) -> str:
        return (
            f"culprit: {culprit}, found in {self.builds_spent} builds "
            f"over a window of {len(self.commits)}"
        )


def breakage_after(broken_from: str, commits: list[str]) -> Callable[[str], bool]:
    """A predicate for tests: red at and after the named commit."""
    index = commits.index(broken_from)

    def is_broken_at(commit: str) -> bool:
        return commits.index(commit) >= index

    return is_broken_at
