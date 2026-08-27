from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.overcommit import (
    MemoryDay,
    lease_plan,
    oom_postmortem,
    safe_ratio,
)

QUIET = MemoryDay(
    label="tuesday", declared_sum=200, peak_concurrent_use=60
)
RELEASE = MemoryDay(
    label="release-day",
    declared_sum=200,
    peak_concurrent_use=110,
)


class TestTheRatio:
    def test_the_worst_day_sets_the_floor(self):
        assert safe_ratio(128, [QUIET, RELEASE]) == pytest.approx(
            128 / 110
        )

    def test_lying_declarations_are_someone_elses_module(self):
        with pytest.raises(Invalid) as caught:
            MemoryDay(
                label="odd",
                declared_sum=50,
                peak_concurrent_use=60,
            )
        assert "different module's problem" in str(caught.value)

    def test_no_observations_no_lease(self):
        with pytest.raises(Invalid):
            safe_ratio(128, [])


class TestThePlan:
    def test_the_correlated_day_is_a_calendar_event(self):
        plan = lease_plan(128, [QUIET, RELEASE])
        assert (
            "worst observed alignment 110 on release-day"
        ) in plan
        assert "commit up to 148 declared (1.2x)" in plan
        assert "calendars repeat" in plan

    def test_a_quiet_workload_recovers_its_gigabytes(self):
        plan = lease_plan(128, [QUIET])
        assert "(2.1x)" in plan
        assert "quiet gigabytes recovered" in plan


class TestThePostmortem:
    def test_the_held_bet_is_credited(self):
        verdict = oom_postmortem(128, QUIET, ratio_used=1.5)
        assert "the bet held" in verdict

    def test_the_oom_day_names_the_sizing_error(self):
        big_day = MemoryDay(
            label="all-linkers-at-once",
            declared_sum=400,
            peak_concurrent_use=180,
        )
        verdict = oom_postmortem(128, big_day, ratio_used=2.0)
        assert "256 was promised against 128 physical" in verdict
        assert "a victim nobody nominated" in verdict
        assert "sized on optimism" in verdict
