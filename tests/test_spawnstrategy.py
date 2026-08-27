from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.spawnstrategy import StrategyChooser


class TestTheTable:
    def test_a_clean_record_runs_observed(self):
        chooser = StrategyChooser()
        assert chooser.choose(
            "compile", cost=8, same_tool_siblings=0
        ) == "observe"

    def test_a_leak_sends_the_rule_to_the_sandbox(self):
        chooser = StrategyChooser()
        chooser.observed_leak("compile")
        assert chooser.choose(
            "compile", cost=8, same_tool_siblings=0
        ) == "sandbox"

    def test_parole_needs_consecutive_clean_runs(self):
        chooser = StrategyChooser()
        chooser.observed_leak("compile")
        for _ in range(2):
            chooser.observed_clean("compile")
        assert chooser.choose(
            "compile", cost=8, same_tool_siblings=0
        ) == "sandbox"
        chooser.observed_clean("compile")
        assert chooser.choose(
            "compile", cost=8, same_tool_siblings=0
        ) == "observe"

    def test_a_new_leak_resets_the_streak(self):
        chooser = StrategyChooser()
        chooser.observed_leak("compile")
        chooser.observed_clean("compile")
        chooser.observed_clean("compile")
        chooser.observed_leak("compile")
        chooser.observed_clean("compile")
        chooser.observed_clean("compile")
        chooser.observed_clean("compile")
        assert chooser.choose(
            "compile", cost=8, same_tool_siblings=0
        ) == "observe"

    def test_cheap_fleets_batch(self):
        chooser = StrategyChooser()
        assert chooser.choose(
            "lint0", cost=1, same_tool_siblings=7
        ) == "batch"

    def test_a_lonely_cheap_rule_observes(self):
        chooser = StrategyChooser()
        assert chooser.choose(
            "lint0", cost=1, same_tool_siblings=1
        ) == "observe"

    def test_negative_costs_are_refused(self):
        with pytest.raises(Invalid):
            StrategyChooser().choose("x", cost=-1, same_tool_siblings=0)


class TestTheReports:
    def test_the_mix_reads_as_percentages(self):
        chooser = StrategyChooser()
        chooser.observed_leak("dirty")
        chooser.choose("dirty", cost=5, same_tool_siblings=0)
        chooser.choose("clean", cost=5, same_tool_siblings=0)
        chooser.choose("lint0", cost=1, same_tool_siblings=4)
        chooser.choose("lint1", cost=1, same_tool_siblings=4)
        report = chooser.mix_report()
        assert "observe 25%" in report
        assert "sandbox 25%" in report
        assert "batch 50%" in report
        assert "hospital, not a home" in report

    def test_a_healthy_fleet_has_an_empty_ward(self):
        chooser = StrategyChooser()
        chooser.choose("a", cost=5, same_tool_siblings=0)
        assert "the ward is empty" in chooser.mix_report()

    def test_explain_returns_the_latest_choice(self):
        chooser = StrategyChooser()
        chooser.observed_leak("compile")
        chooser.choose("compile", cost=8, same_tool_siblings=0)
        explanation = chooser.explain("compile")
        assert explanation.startswith("compile: sandbox")
        assert "from parole" in explanation

    def test_the_unchosen_are_refused(self):
        with pytest.raises(Invalid):
            StrategyChooser().explain("ghost")
