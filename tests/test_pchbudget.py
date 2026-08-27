from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.pchbudget import (
    Header,
    appraise,
    plan,
    stability_price,
)

STL_WRAP = Header(
    name="stl_wrap.h",
    parse_ticks=9,
    inclusions=400,
    edits_per_week=0,
    rebuild_ticks_per_includer=12,
)
GOD_HEADER = Header(
    name="everything.h",
    parse_ticks=9,
    inclusions=400,
    edits_per_week=60,
    rebuild_ticks_per_includer=12,
)
LEAF = Header(
    name="tiny.h",
    parse_ticks=1,
    inclusions=3,
    edits_per_week=1,
    rebuild_ticks_per_includer=2,
)


class TestAppraisal:
    def test_the_stable_wide_header_earns_it(self):
        verdict = appraise(STL_WRAP)
        assert verdict.weekly_saving == 180000
        assert verdict.weekly_blast == 0
        assert verdict.worth_it()

    def test_the_churning_god_header_loses(self):
        verdict = appraise(GOD_HEADER)
        assert verdict.weekly_saving == 180000
        assert verdict.weekly_blast == 288000
        assert not verdict.worth_it()

    def test_the_same_width_lands_on_both_sides(self):
        assert (
            appraise(STL_WRAP).weekly_saving
            == appraise(GOD_HEADER).weekly_saving
        )

    def test_bad_numbers_are_refused(self):
        with pytest.raises(Invalid):
            Header(
                name="x",
                parse_ticks=0,
                inclusions=1,
                edits_per_week=0,
                rebuild_ticks_per_includer=1,
            )


class TestThePlan:
    def test_the_plan_ranks_winners_first_with_both_numbers(self):
        report = plan([GOD_HEADER, STL_WRAP, LEAF])
        assert report.startswith(
            "2 of 3 header(s) earn precompilation"
        )
        lines = report.splitlines()
        assert lines[1].startswith("  stl_wrap.h: saves 180000")
        assert "leave it plain" in lines[3]

    def test_an_empty_plan_is_refused(self):
        with pytest.raises(Invalid):
            plan([])


class TestTheStabilityPrice:
    def test_the_loser_gets_its_breakeven_churn(self):
        advice = stability_price(GOD_HEADER)
        assert "at 37 edit(s) a week or fewer" in advice
        assert "it sees 60" in advice
        assert "the fix is stability, not tooling" in advice

    def test_the_winner_is_left_alone(self):
        advice = stability_price(STL_WRAP)
        assert "already earns its keep" in advice
