from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.mtimeworld import TwoWorldTracker


def fresh() -> TwoWorldTracker:
    tracker = TwoWorldTracker()
    tracker.save("main.c", b"int main;", clock=0)
    tracker.build("main.o", "main.c", clock=1)
    return tracker


class TestAgreement:
    def test_a_real_change_rebuilds_in_both_worlds(self):
        tracker = fresh()
        tracker.save("main.c", b"int main; // v2", clock=5)
        verdict = tracker.build("main.o", "main.c", clock=6)
        assert verdict == {"mtime": "rebuild", "content": "rebuild"}
        assert tracker.false_rebuilds == 0

    def test_an_untouched_world_skips_in_both(self):
        tracker = fresh()
        verdict = tracker.build("main.o", "main.c", clock=2)
        assert verdict == {"mtime": "skip", "content": "skip"}


class TestTheTouchLie:
    def test_a_touch_rebuilds_for_the_clock_only(self):
        tracker = fresh()
        tracker.touch("main.c", clock=5)
        verdict = tracker.build("main.o", "main.c", clock=6)
        assert verdict == {"mtime": "rebuild", "content": "skip"}
        assert tracker.false_rebuilds == 1

    def test_a_checkout_storm_bills_per_touch(self):
        tracker = fresh()
        for clock in range(5, 10):
            tracker.touch("main.c", clock=clock)
            tracker.build("main.o", "main.c", clock=clock)
        assert tracker.false_rebuilds == 5

    def test_touching_the_missing_is_refused(self):
        with pytest.raises(Invalid):
            TwoWorldTracker().touch("ghost.c", clock=1)


class TestTheClockLie:
    def test_a_same_tick_change_ships_stale(self):
        tracker = TwoWorldTracker()
        tracker.save("main.c", b"int main;", clock=5)
        tracker.build("main.o", "main.c", clock=5)
        tracker.save("main.c", b"int main; // rushed", clock=5)
        verdict = tracker.build("main.o", "main.c", clock=6)
        assert verdict == {"mtime": "skip", "content": "rebuild"}
        assert tracker.stale_serves == ["main.o"]

    def test_the_receipt_shapes_the_two_failures_differently(self):
        tracker = fresh()
        tracker.touch("main.c", clock=5)
        tracker.build("main.o", "main.c", clock=6)
        assert tracker.receipt() == (
            "1 false rebuilds, no stale serves; the clock only "
            "wasted time today"
        )
        tracker.save("main.c", b"changed", clock=7)
        tracker.build("main.o", "main.c", clock=7)
        tracker.save("main.c", b"changed again", clock=7)
        tracker.build("main.o", "main.c", clock=8)
        assert "the clock shipped stale: ['main.o']" in tracker.receipt()
