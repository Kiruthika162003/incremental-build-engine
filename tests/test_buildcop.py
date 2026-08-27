from __future__ import annotations

import pytest

from forge.buildcop import QUARANTINE_TICKS, BuildCop
from forge.errors import Invalid, Missing

TARGETS = ["auth_test", "billing_test", "search_test"]


def cop_with_one() -> BuildCop:
    cop = BuildCop()
    cop.quarantine(
        "billing_test", owner="li", issue="ISSUE-42", now=0
    )
    return cop


class TestQuarantine:
    def test_entry_demands_the_paperwork(self):
        with pytest.raises(Invalid, match="optimistic signage"):
            BuildCop().quarantine("x", owner=" ", issue="", now=0)

    def test_the_blocking_set_shrinks_and_days_resume(self):
        cop = cop_with_one()
        assert cop.blocking_set(TARGETS) == [
            "auth_test",
            "search_test",
        ]

    def test_double_quarantine_is_refused(self):
        cop = cop_with_one()
        with pytest.raises(Invalid):
            cop.quarantine(
                "billing_test", owner="li", issue="ISSUE-42", now=1
            )


class TestTheExit:
    def test_one_pass_is_not_enough(self):
        cop = cop_with_one()
        verdict = cop.record_run("billing_test", passed=True)
        assert "one more before it rejoins" in verdict

    def test_two_passes_rejoin_the_blocking_set(self):
        cop = cop_with_one()
        cop.record_run("billing_test", passed=True)
        verdict = cop.record_run("billing_test", passed=True)
        assert "rejoins the blocking set" in verdict
        assert cop.blocking_set(TARGETS) == sorted(TARGETS)

    def test_a_failure_resets_the_exit_streak(self):
        cop = cop_with_one()
        cop.record_run("billing_test", passed=True)
        cop.record_run("billing_test", passed=False)
        verdict = cop.record_run("billing_test", passed=True)
        assert "one more" in verdict

    def test_recording_the_unquarantined_is_refused(self):
        with pytest.raises(Missing):
            cop_with_one().record_run("auth_test", passed=True)


class TestPatrol:
    def test_expiry_escalates_instead_of_extending(self):
        cop = cop_with_one()
        flagged = cop.patrol(now=QUARANTINE_TICKS)
        assert flagged == [
            "billing_test: expired in quarantine; escalating past "
            "li on ISSUE-42"
        ]

    def test_escalation_fires_once_not_weekly(self):
        cop = cop_with_one()
        cop.patrol(now=QUARANTINE_TICKS)
        assert cop.patrol(now=QUARANTINE_TICKS + 10) == []

    def test_the_report_names_the_oldest_resident(self):
        cop = cop_with_one()
        cop.quarantine(
            "search_test", owner="raj", issue="ISSUE-77", now=30
        )
        report = cop.report(now=40)
        assert "billing_test: 40 ticks inside" in report
        assert (
            "the oldest resident is billing_test at 40 ticks" in report
        )

    def test_an_empty_quarantine_counts_its_alumni(self):
        cop = cop_with_one()
        cop.record_run("billing_test", passed=True)
        cop.record_run("billing_test", passed=True)
        assert cop.report(now=10) == (
            "quarantine empty; 1 rejoined to date"
        )
