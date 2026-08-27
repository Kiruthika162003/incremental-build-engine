"""The warmer graded on a real morning: exact where it can be.

Yesterday's merge touched the core; the warmer packs the core's
five-target cone dearest-first into a 60-tick budget, and the
guess said four would fit. The measurement says three: pkg, app,
and bench spend the budget to the exact tick and both cheap
targets are priced out, so the morning scores three warm, three
cold, zero wasted, and the diagnosis says timid. Raising the
budget to 100 fits the whole 82-tick cone: five warm, one cold,
still zero wasted, and the survivor is the unpredictable
stranger, which is the warmer's honest ceiling: prediction ends
where the merge's cone does.
"""

from __future__ import annotations

from forge.audits.finding import Finding
from forge.cachewarm import MorningScore, Warmer
from forge.graph import Graph


def _overnight() -> Warmer:
    graph = Graph()
    graph.declare("core.c")
    graph.declare("core.o", needs=("core.c",))
    graph.declare("app", needs=("core.o",))
    graph.declare("bench", needs=("core.o",))
    graph.declare("docs", needs=("core.o",))
    graph.declare("pkg", needs=("app",))
    return Warmer(
        graph=graph,
        costs={
            "core.o": 10,
            "app": 20,
            "bench": 15,
            "docs": 12,
            "pkg": 25,
        },
    )


MORNING = ["core.o", "app", "bench", "docs", "pkg", "surprise"]


def _score(budget: int) -> MorningScore:
    plan = _overnight().plan(["core.c"], budget=budget)
    score = MorningScore(warmed=set(plan.predicted))
    for request in MORNING:
        score.request(request)
    return score


def run() -> Finding:
    tight = _score(budget=60)
    roomy = _score(budget=100)
    numbers = {
        "tight_cold": len(tight.cold_misses()),
        "tight_wasted": len(tight.wasted_warmth()),
        "tight_diagnosis_timid": tight.diagnosis().startswith("timid"),
        "roomy_cold": len(roomy.cold_misses()),
        "roomy_wasted": len(roomy.wasted_warmth()),
        "ceiling_is_the_stranger": roomy.cold_misses() == ["surprise"],
    }
    holds = (
        numbers["tight_cold"] == 3
        and numbers["tight_wasted"] == 0
        and numbers["tight_diagnosis_timid"]
        and numbers["roomy_cold"] == 1
        and numbers["roomy_wasted"] == 0
        and numbers["ceiling_is_the_stranger"]
    )
    return Finding(
        audit="warmscore",
        claim=(
            "dearest-first spends 60 ticks on three targets to the "
            "exact tick; the roomy budget warms the whole cone and "
            "only the stranger stays cold"
        ),
        numbers=numbers,
        holds=holds,
    )
