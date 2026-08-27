from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.reformat import ReformatSim, policy_advice


class TestBigBang:
    def test_one_commit_buys_uniformity_forever(self):
        sim = ReformatSim(files=1000, hot_files=200)
        verdict = sim.big_bang()
        assert "a day of frozen merges" in verdict
        assert sim.coverage() == 1.0

    def test_a_tree_without_hot_files_is_refused(self):
        with pytest.raises(Invalid):
            ReformatSim(files=100, hot_files=0)


class TestTouchStyle:
    def test_twelve_weeks_covers_the_hot_half_then_flatlines(self):
        sim = ReformatSim(files=1000, hot_files=200)
        report = sim.convergence_report(12)
        assert report.startswith(
            "after 12 week(s): 13% of the tree, 127 of 200 "
            "hot file(s), 0 of 800 cold"
        )
        assert "cold precisely because nobody touches them" in (
            report
        )

    def test_more_weeks_never_reach_the_cold_files(self):
        sim = ReformatSim(files=1000, hot_files=200)
        sim.convergence_report(50)
        cold_touched = [
            f for f in sim.formatted if f >= 200
        ]
        assert cold_touched == []


class TestTheAdvice:
    def test_the_hybrid_is_recommended_with_its_unit(self):
        advice = policy_advice(1000, 200, 12)
        assert "sweep the 800 cold file(s) on a schedule" in (
            advice
        )
        assert (
            "one commit per cold directory instead of one per "
            "fleet"
        ) in advice
