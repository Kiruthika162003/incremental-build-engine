from __future__ import annotations

import pytest

from forge.bumpplan import Bump, BumpPlanner
from forge.errors import Invalid


def planner() -> BumpPlanner:
    built = BumpPlanner()
    built.add(Bump(package="leftpad", jump="patch", fan_in=1))
    built.add(Bump(package="httplib", jump="major", fan_in=8))
    built.add(Bump(package="tlslib", jump="minor", fan_in=8))
    built.add(Bump(package="fmtlib", jump="minor", fan_in=2))
    return built


class TestRisk:
    def test_risk_is_jump_times_fan_in(self):
        assert Bump(
            package="x", jump="major", fan_in=8
        ).risk() == 72

    def test_a_leaf_still_carries_its_jump_weight(self):
        assert Bump(
            package="x", jump="minor", fan_in=0
        ).risk() == 3

    def test_a_wild_jump_kind_is_refused(self):
        with pytest.raises(Invalid):
            Bump(package="x", jump="yolo", fan_in=1)


class TestThePlan:
    def test_the_plan_lands_riskiest_last(self):
        report = planner().plan()
        lines = report.splitlines()
        assert lines[0] == (
            "4 bump(s) in 4 landing(s), riskiest last"
        )
        assert lines[1] == "  1. leftpad (risk 1)"
        assert lines[2] == "  2. fmtlib (risk 6)"
        assert lines[3] == "  3. tlslib (risk 24)"
        assert lines[4] == "  4. httplib (risk 72)"

    def test_tied_bumps_fuse_with_the_reason_shown(self):
        built = planner()
        built.tie(
            "httplib",
            "tlslib",
            "httplib 3.x requires tlslib >= 1.8",
        )
        report = built.plan()
        assert "3 landing(s)" in report
        assert "httplib + tlslib (risk 96)" in report
        assert (
            "fused: httplib 3.x requires tlslib >= 1.8" in report
        )

    def test_a_tie_needs_both_ends_planned(self):
        with pytest.raises(Invalid):
            planner().tie("httplib", "ghost", "because")

    def test_an_empty_plan_is_refused(self):
        with pytest.raises(Invalid):
            BumpPlanner().plan()

    def test_double_planning_a_package_is_refused(self):
        built = planner()
        with pytest.raises(Invalid):
            built.add(
                Bump(package="leftpad", jump="minor", fan_in=1)
            )


class TestTheHaystack:
    def test_the_price_names_both_worlds(self):
        line = planner().haystack_price()
        assert "suspects at most the latest landing" in line
        assert "suspects all 4" in line
        assert "4 landings buy that difference" in line
