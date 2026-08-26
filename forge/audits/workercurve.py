"""The worker curve bends at the graph's width, not at the budget's edge.

One build simulated at every pool size from one to twelve: a
two-stage graph, eight parallel compiles feeding one link, total
work 68 ticks, critical path 12. The guess was a gentle staircase
where the fifth worker still buys a little; the measurement is
harsher: with eight equal compiles the wave count is ceil(8/w), so
the fifth, sixth, and seventh workers buy exactly nothing, stuck
at two waves like the fourth, and only the eighth collapses the
compiles into one wave and lands the 12-tick floor. Past eight,
nothing again. The curve is not a slope, it is two cliffs, and a
capacity plan that budgets workers five through seven has bought
three salaries of idle time.
"""

from __future__ import annotations

from forge.audits.finding import Finding
from forge.graph import Graph
from forge.scheduler import Scheduler

COMPILES = 8
COMPILE_COST = 8
LINK_COST = 4


def _build() -> Scheduler:
    graph = Graph()
    graph.declare("gen")
    for number in range(COMPILES):
        graph.declare(f"unit{number}.o", needs=("gen",))
    graph.declare(
        "app",
        needs=tuple(f"unit{number}.o" for number in range(COMPILES)),
    )
    costs = {"gen": 0, "app": LINK_COST}
    costs.update(
        {f"unit{number}.o": COMPILE_COST for number in range(COMPILES)}
    )
    return Scheduler(graph=graph, costs=costs)


def run() -> Finding:
    build = _build()
    floor, _ = build.critical_path("app")
    curve = {
        workers: build.simulate("app", workers).makespan
        for workers in range(1, 13)
    }
    numbers = {
        "one_worker": curve[1],
        "four_workers": curve[4],
        "eight_workers": curve[8],
        "twelve_workers": curve[12],
        "floor": floor,
        "fifth_worker_buys": curve[4] - curve[5],
        "seventh_worker_buys": curve[6] - curve[7],
        "eighth_worker_buys": curve[7] - curve[8],
        "ninth_worker_buys": curve[8] - curve[9],
    }
    holds = (
        curve[1] == 68
        and curve[8] == floor == 12
        and curve[12] == curve[8]
        and numbers["fifth_worker_buys"] == 0
        and numbers["seventh_worker_buys"] == 0
        and numbers["eighth_worker_buys"] == 8
        and numbers["ninth_worker_buys"] == 0
    )
    return Finding(
        audit="workercurve",
        claim=(
            "workers five through seven buy exactly nothing; the "
            "eighth buys eight ticks and lands the floor: two cliffs, "
            "not a slope"
        ),
        numbers=numbers,
        holds=holds,
    )
