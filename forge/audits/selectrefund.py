"""The test-selection refund grows with the repository; the tax does not.

A repository of twenty modules, each with a test, all sharing one
common core. The guess was two tests selected on a leaf edit; the
measurement says one, the module's own, since the graph fans out
from the core rather than through it: a 95 percent refund. An edit
to the shared core selects all twenty, refund zero, which is the
honest floor: selection is not a discount on risky changes, it is
a discount on contained ones. Doubling the module count lifts the
leaf refund to 98 percent while the core refund stays zero, which
pins the economics: the refund on leaf edits scales with
repository size, and leaf edits are what a working day is mostly
made of.
"""

from __future__ import annotations

from forge.audits.finding import Finding
from forge.graph import Graph
from forge.testselect import Selector


def _repository(modules: int) -> Selector:
    graph = Graph()
    graph.declare("core.c")
    graph.declare("core.o", needs=("core.c",))
    for number in range(modules):
        graph.declare(f"mod{number}.c")
        graph.declare(
            f"mod{number}.o", needs=(f"mod{number}.c", "core.o")
        )
        graph.declare(f"mod{number}_test", needs=(f"mod{number}.o",))
    selector = Selector(graph=graph)
    for number in range(modules):
        selector.mark_test(f"mod{number}_test")
    return selector


def run() -> Finding:
    twenty = _repository(20)
    leaf = twenty.select(["mod3.c"])
    core = twenty.select(["core.c"])
    forty = _repository(40)
    leaf_at_forty = forty.select(["mod3.c"])
    numbers = {
        "leaf_selected": len(leaf.selected),
        "leaf_refund_pct": round(leaf.refund() * 100),
        "core_selected": len(core.selected),
        "core_refund_pct": round(core.refund() * 100),
        "leaf_refund_at_double_size_pct": round(
            leaf_at_forty.refund() * 100
        ),
    }
    holds = (
        leaf.selected == ["mod3_test"]
        and numbers["leaf_refund_pct"] == 95
        and numbers["core_selected"] == 20
        and numbers["core_refund_pct"] == 0
        and numbers["leaf_refund_at_double_size_pct"] == 98
    )
    return Finding(
        audit="selectrefund",
        claim=(
            "a leaf edit selects one test of twenty and the refund "
            "climbs with repository size; a core edit refunds zero, "
            "the honest floor"
        ),
        numbers=numbers,
        holds=holds,
    )
