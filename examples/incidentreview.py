"""The incident review: traces, fences, glass, and the restated quarter.

Run with: python -m examples.incidentreview
"""

from __future__ import annotations

import contextlib

from forge.breakglass import BreakGlass
from forge.errorbudget import ErrorBudget
from forge.errors import Invalid
from forge.leaselock import LeaseStore
from forge.restatement import MetricHistory
from forge.tracestitch import Span, TraceStitcher


def exhibit_a_the_trace():
    stitcher = TraceStitcher()
    stitcher.collect(Span("t1", "coordinator", 0, 2, "accepted"))
    stitcher.collect(Span("t1", "worker", 5, 90, "ran compile"))
    stitcher.collect(Span("t1", "store", 96, 4, "uploaded"))
    report = stitcher.timeline("t1")
    print(f"exhibit A: {report.splitlines()[0]}")
    print(f"           {report.splitlines()[-1].strip()}")


def exhibit_b_the_fence():
    store = LeaseStore()
    store.acquire("coord-a", now=0)
    store.write("coord-a", 1, "state-v1")
    store.acquire("coord-b", now=31)
    store.write("coord-b", 2, "state-v2")
    with contextlib.suppress(Invalid):
        store.write("coord-a", 1, "stale-state")
    print(f"exhibit B: {store.incident_summary()}")


def exhibit_c_the_glass():
    glass = BreakGlass(
        incident="INC-441 cache poisoning",
        human="kiruthika",
        opened_at=100,
        expires_at=160,
    )
    glass.act("quarantined the poisoned digest", now=110)
    print(f"exhibit C: {glass.close(now=125)}")


def exhibit_d_the_budget():
    budget = ErrorBudget(window_builds=10000, promise_percent=99.0)
    budget.burn("cache-corruption", 70)
    print(
        "exhibit D: "
        + budget.burn("cache-corruption", 40)
    )


def exhibit_e_the_restatement():
    history = MetricHistory(metric="cache-hit-rate")
    history.publish("2031-q2", 95.5)
    print(
        "exhibit E: "
        + history.restate(
            "2031-q2",
            88.0,
            defect="the poisoned week counted as hits",
        )
    )


def main() -> int:
    exhibit_a_the_trace()
    exhibit_b_the_fence()
    exhibit_c_the_glass()
    exhibit_d_the_budget()
    exhibit_e_the_restatement()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
