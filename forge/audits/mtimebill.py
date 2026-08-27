"""One scripted week bills the timestamp model in both currencies.

Five working days over one file: Monday a real edit, Tuesday a
checkout touch, Wednesday two rushed saves inside one clock tick,
Thursday another touch, Friday a real edit. The guess said four
false rebuilds; the measurement says two, one per checkout touch,
because the clock model at least skips when nothing bumped it.
Wednesday still ships its stale artifact, the second rushed save
hiding inside the tick, which is the asymmetry the audit exists
to display: the
waste column holds a number you pay in minutes, the staleness
column holds a name you pay in trust, and a model that produces
both at once is not a compromise, it is the worst of each.
"""

from __future__ import annotations

from forge.audits.finding import Finding
from forge.mtimeworld import TwoWorldTracker


def _week() -> TwoWorldTracker:
    tracker = TwoWorldTracker()
    tracker.save("app.c", b"int app;", clock=0)
    tracker.build("app.o", "app.c", clock=1)

    tracker.save("app.c", b"int app; // monday", clock=10)
    tracker.build("app.o", "app.c", clock=11)

    tracker.touch("app.c", clock=20)
    tracker.build("app.o", "app.c", clock=21)

    tracker.save("app.c", b"int app; // wed", clock=30)
    tracker.build("app.o", "app.c", clock=30)
    tracker.save("app.c", b"int app; // wed rushed", clock=30)
    tracker.build("app.o", "app.c", clock=31)

    tracker.touch("app.c", clock=40)
    tracker.build("app.o", "app.c", clock=41)

    tracker.save("app.c", b"int app; // friday", clock=50)
    tracker.build("app.o", "app.c", clock=51)
    return tracker


def run() -> Finding:
    tracker = _week()
    numbers = {
        "false_rebuilds": tracker.false_rebuilds,
        "stale_serves": len(tracker.stale_serves),
        "stale_named": tracker.stale_serves == ["app.o"],
    }
    holds = (
        tracker.false_rebuilds == 2
        and tracker.stale_serves == ["app.o"]
    )
    return Finding(
        audit="mtimebill",
        claim=(
            "the week bills the clock twice over: two false rebuilds "
            "paid in minutes and one stale serve paid in trust, and a "
            "model producing both is the worst of each"
        ),
        numbers=numbers,
        holds=holds,
    )
