"""Priority inversion: the intern's job holds the lock the release needs.

The farm's oldest scheduling injury has three actors: a batch
action holding the output-tree lock, a release build waiting
for it, and a parade of medium-priority work that preempts the
batch action precisely because it is low priority, leaving the
release waiting on a job that cannot run. Priority inheritance
is the fix with the funny name and the serious effect: while a
high-priority action waits on a lock, the holder borrows the
waiter's priority, finishes without being preempted, and
returns to obscurity when it releases. The simulator runs the
same contention with and without inheritance and prints both
waits side by side, because the pattern is invisible until it
is measured, and the measured gap is usually the width of the
parade, not of the lock.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid


@dataclass(frozen=True)
class Contention:
    holder_ticks_left: int
    parade_jobs: int
    parade_ticks_each: int

    def __post_init__(self) -> None:
        if self.holder_ticks_left <= 0:
            raise Invalid(
                "a holder with no work left is not holding"
            )
        if self.parade_jobs < 0 or self.parade_ticks_each < 0:
            raise Invalid("the parade cannot be negative")


def wait_without_inheritance(contention: Contention) -> int:
    parade = (
        contention.parade_jobs * contention.parade_ticks_each
    )
    return parade + contention.holder_ticks_left


def wait_with_inheritance(contention: Contention) -> int:
    return contention.holder_ticks_left


def comparison(contention: Contention) -> str:
    without = wait_without_inheritance(contention)
    with_it = wait_with_inheritance(contention)
    parade = without - with_it
    return (
        f"the release waits {without} tick(s) without "
        f"inheritance and {with_it} with it; the {parade}-tick "
        "gap is the width of the parade, not of the lock"
    )


@dataclass
class LockLedger:
    inversions_seen: int = 0
    parade_ticks_avoided: int = 0

    def observe(self, contention: Contention) -> str:
        self.inversions_seen += 1
        avoided = wait_without_inheritance(
            contention
        ) - wait_with_inheritance(contention)
        self.parade_ticks_avoided += avoided
        return (
            f"inversion #{self.inversions_seen}: the holder "
            "borrows the waiter's priority, finishes "
            "unpreempted, and returns to obscurity"
        )

    def season_report(self) -> str:
        if self.inversions_seen == 0:
            raise Invalid(
                "no inversions observed; either the locks are "
                "uncontended or nobody is looking"
            )
        return (
            f"{self.inversions_seen} inversion(s), "
            f"{self.parade_ticks_avoided} parade tick(s) "
            "avoided; invisible until measured"
        )
