"""The merge queue: optimism batched, pessimism proven, blame precise.

Testing every pull request against head serially is safe and slow;
merging optimistically is fast until the day two changes conflict
semantically and main goes red. The queue takes the middle road:
batch the pending changes, build the batch once, and on green
merge all of them for one build's price. On red the batch splits
in half and each half builds alone, recursively, which is culprit
finding folded into admission: the guilty change is exiled with
its name, the innocent halves merge, and the ledger prices the
whole affair in builds per merged change. The worst case is a
batch of mutual conflicts degenerating to serial, and the ledger
shows that too, because a merge queue's value is a ratio, not a
promise.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class QueueLedger:
    builds: int = 0
    merged: list[str] = field(default_factory=list)
    exiled: list[str] = field(default_factory=list)

    def price(self) -> str:
        if not self.merged and not self.exiled:
            raise Invalid("nothing was processed; there is no price")
        per_merge = (
            round(self.builds / len(self.merged), 2)
            if self.merged
            else float("inf")
        )
        return (
            f"{self.builds} builds for {len(self.merged)} merges "
            f"({per_merge} builds per change), "
            f"{len(self.exiled)} exiled"
        )


def process_batch(
    changes: list[str],
    batch_is_green: Callable[[list[str]], bool],
    ledger: QueueLedger,
) -> None:
    if not changes:
        return
    ledger.builds += 1
    if batch_is_green(changes):
        ledger.merged.extend(changes)
        return
    if len(changes) == 1:
        ledger.exiled.append(changes[0])
        return
    middle = len(changes) // 2
    process_batch(changes[:middle], batch_is_green, ledger)
    process_batch(changes[middle:], batch_is_green, ledger)


def run_queue(
    changes: list[str],
    batch_is_green: Callable[[list[str]], bool],
) -> QueueLedger:
    if not changes:
        raise Invalid("an empty queue has nothing to merge")
    ledger = QueueLedger()
    process_batch(list(changes), batch_is_green, ledger)
    return ledger


def conflicts_with(broken: set[str]) -> Callable[[list[str]], bool]:
    """A predicate for tests: green unless a broken change is aboard."""

    def batch_is_green(changes: list[str]) -> bool:
        return not (set(changes) & broken)

    return batch_is_green
