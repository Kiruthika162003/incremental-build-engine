"""Delta debugging: the failing build shrinks to the inputs that matter.

A build that fails with four hundred inputs is a haystack; the
same failure reproduced by three inputs is a bug report. The
minimizer runs the classic ddmin loop: split the failing set
into chunks, test whether any chunk alone still fails, then
whether the set minus any chunk still fails, and refine the
granularity when neither helps, until the set is 1-minimal,
meaning every remaining input is load-bearing: remove any one
and the failure disappears. The oracle bill is printed with the
result because minimization is a purchase, oracle runs are real
builds, and the guess of the price was optimistic: the prose
first claimed nineteen builds, the measured drill says a single
culprit in sixteen inputs costs 8 builds and an interacting
pair costs 49, because pairs defeat the keep-a-chunk shortcut
and pay full complement fare at every granularity. Still a
bargain any afternoon the bug is confusing enough, but the
meter, not the sales pitch, sets the price.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from forge.errors import Invalid

Oracle = Callable[[frozenset[str]], bool]


@dataclass
class Minimizer:
    oracle: Oracle
    oracle_calls: int = 0
    trace: list[str] = field(default_factory=list)

    def _fails(self, inputs: frozenset[str]) -> bool:
        self.oracle_calls += 1
        return self.oracle(inputs)

    def minimize(self, inputs: tuple[str, ...]) -> list[str]:
        if not inputs:
            raise Invalid("nothing to minimize")
        current = frozenset(inputs)
        if not self._fails(current):
            raise Invalid(
                "the full set does not fail; there is nothing "
                "to shrink toward"
            )
        chunks = 2
        while len(current) >= 2:
            pieces = self._split(sorted(current), chunks)
            reduced = False
            for piece in pieces:
                candidate = frozenset(piece)
                if self._fails(candidate):
                    current = candidate
                    chunks = 2
                    reduced = True
                    self.trace.append(
                        f"kept a chunk of {len(candidate)}"
                    )
                    break
            if not reduced:
                for piece in pieces:
                    candidate = current - frozenset(piece)
                    if candidate and self._fails(candidate):
                        current = candidate
                        chunks = max(chunks - 1, 2)
                        reduced = True
                        self.trace.append(
                            f"dropped a chunk, kept "
                            f"{len(candidate)}"
                        )
                        break
            if not reduced:
                if chunks >= len(current):
                    break
                chunks = min(len(current), chunks * 2)
                self.trace.append(
                    f"refined granularity to {chunks}"
                )
        return sorted(current)

    @staticmethod
    def _split(items: list[str], chunks: int) -> list[list[str]]:
        size = max(1, len(items) // chunks)
        return [
            items[start : start + size]
            for start in range(0, len(items), size)
        ]

    def bill(self, before: int, after: int) -> str:
        return (
            f"{before} input(s) became {after} for the price of "
            f"{self.oracle_calls} build(s)"
        )
