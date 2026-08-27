from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.thermal import (
    hour_report,
    pin_everything,
    sprint_and_rest,
)


class TestTheTwoStrategies:
    def test_pinning_throttles_most_of_the_hour(self):
        pinned = pin_everything(120)
        assert pinned.work_done == pytest.approx(63.0)
        assert pinned.throttled_ticks == 95

    def test_resting_a_third_of_the_hour_still_wins(self):
        rested = sprint_and_rest(120, sprint=15, rest=10)
        assert rested.work_done == pytest.approx(75.0)
        assert rested.throttled_ticks == 0

    def test_a_greedy_sprint_starts_paying_throttle(self):
        greedy = sprint_and_rest(120, sprint=20, rest=8)
        assert greedy.throttled_ticks == 41
        assert greedy.work_done < 65

    def test_empty_and_nonsense_schedules_are_refused(self):
        with pytest.raises(Invalid):
            pin_everything(0)
        with pytest.raises(Invalid):
            sprint_and_rest(60, sprint=0, rest=5)


class TestTheReport:
    def test_the_hour_report_shows_both_ledgers(self):
        report = hour_report(120, sprint=20, rest=10)
        assert (
            "pin-everything did 63 work with 95 throttled "
            "tick(s)"
        ) in report
        assert "sprint 20/rest 10 did 71 with 15" in report
        assert "sprint-and-rest wins" in report
        assert "the rests did nothing except everything" in report
