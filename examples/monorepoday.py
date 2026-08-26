"""A monorepo day: edits, selection, the queue, and one culprit.

Run with: python -m examples.monorepoday
"""

from __future__ import annotations

from forge.culprit import Hunt, breakage_after
from forge.graph import Graph
from forge.mergequeue import conflicts_with, run_queue
from forge.testselect import Selector


def repository() -> Selector:
    graph = Graph()
    graph.declare("core.c")
    graph.declare("core.o", needs=("core.c",))
    for team in ("auth", "billing", "search", "admin"):
        graph.declare(f"{team}.c")
        graph.declare(f"{team}.o", needs=(f"{team}.c", "core.o"))
        graph.declare(f"{team}_test", needs=(f"{team}.o",))
    selector = Selector(graph=graph)
    for team in ("auth", "billing", "search", "admin"):
        selector.mark_test(f"{team}_test")
    return selector


def morning(selector: Selector) -> None:
    contained = selector.select(["billing.c"])
    print(f"morning edit: {contained.line()}")
    risky = selector.select(["core.c"])
    print(f"core edit:    {risky.line()}")


def afternoon() -> None:
    changes = [f"pr{number}" for number in range(6)]
    ledger = run_queue(changes, conflicts_with({"pr4"}))
    print(f"merge queue:  {ledger.price()}")
    print(f"exiled:       {', '.join(ledger.exiled)}")


def evening() -> None:
    window = [f"c{number:02d}" for number in range(32)]
    hunt = Hunt(
        commits=window,
        is_broken_at=breakage_after("c19", window),
    )
    culprit = hunt.run()
    print(f"nightly red:  {hunt.receipt(culprit)}")


def main() -> int:
    selector = repository()
    morning(selector)
    afternoon()
    evening()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
