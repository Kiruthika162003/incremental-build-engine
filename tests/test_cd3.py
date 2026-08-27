from __future__ import annotations

import pytest

from forge.cd3 import Project, schedule, total_delay_cost
from forge.errors import Invalid

QUICK_WIN = Project(
    name="preflight-rollout",
    delay_cost_per_week=30,
    duration_weeks=2,
)
FLAGSHIP = Project(
    name="remote-exec-v2",
    delay_cost_per_week=120,
    duration_weeks=12,
)
HUNCH = Project(
    name="ai-something",
    delay_cost_per_week=None,
    duration_weeks=6,
)


class TestTheRatio:
    def test_the_short_cheap_job_beats_the_flagship(self):
        report = schedule([FLAGSHIP, QUICK_WIN])
        lines = report.splitlines()
        assert lines[1].startswith("  1. preflight-rollout")
        assert "30/week over 2 week(s) = 15" in lines[1]
        assert lines[2].startswith("  2. remote-exec-v2")

    def test_the_sponsor_sees_the_number_that_outvoted_them(self):
        report = schedule([FLAGSHIP, QUICK_WIN])
        assert (
            "preflight-rollout outranks remote-exec-v2"
        ) in report

    def test_the_unestimable_sorts_last_with_the_reason(self):
        report = schedule([QUICK_WIN, HUNCH])
        assert (
            "last. ai-something: no defensible cost of delay"
        ) in report
        assert "inside the spreadsheet" in report

    def test_a_durationless_wish_is_refused(self):
        with pytest.raises(Invalid):
            Project(
                name="x",
                delay_cost_per_week=10,
                duration_weeks=0,
            )


class TestTheProof:
    def test_cd3_order_costs_less_than_flagship_first(self):
        cd3_order = [QUICK_WIN, FLAGSHIP]
        flagship_first = [FLAGSHIP, QUICK_WIN]
        assert total_delay_cost(cd3_order) < total_delay_cost(
            flagship_first
        )

    def test_the_totals_are_the_argument_ender(self):
        assert total_delay_cost([QUICK_WIN, FLAGSHIP]) == (
            30 * 2 + 120 * 14
        )
        assert total_delay_cost([FLAGSHIP, QUICK_WIN]) == (
            120 * 12 + 30 * 14
        )
