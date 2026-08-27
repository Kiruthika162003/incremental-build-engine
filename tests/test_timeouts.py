from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.timeouts import DeadlineKeeper


def keeper() -> DeadlineKeeper:
    built = DeadlineKeeper()
    built.learn_p99("quick_lint", 4)
    built.learn_p99("long_link", 600)
    return built


class TestAllowances:
    def test_the_leash_is_personal(self):
        built = keeper()
        assert built.allowance("quick_lint") == 12
        assert built.allowance("long_link") == 1800

    def test_the_minimum_floors_tiny_rules(self):
        built = DeadlineKeeper()
        built.learn_p99("instant", 1)
        assert built.allowance("instant") == 10

    def test_no_history_means_no_deadline_yet(self):
        assert keeper().allowance("newcomer") is None

    def test_nonsense_p99s_are_refused(self):
        with pytest.raises(Invalid):
            DeadlineKeeper().learn_p99("x", 0)


class TestVerdicts:
    def test_the_wedged_quick_rule_is_caught_in_minutes(self):
        built = keeper()
        verdict = built.observe_run("quick_lint", duration=500)
        assert verdict.startswith("KILLED quick_lint at 12")
        assert "overran by 488" in verdict

    def test_the_legitimate_long_link_survives(self):
        built = keeper()
        verdict = built.observe_run("long_link", duration=1500)
        assert "finished at 1500 inside 1800" in verdict

    def test_a_kill_does_not_poison_the_history(self):
        built = keeper()
        built.observe_run("quick_lint", duration=500)
        assert built.allowance("quick_lint") == 12

    def test_the_newcomer_is_watched_not_killed(self):
        verdict = keeper().observe_run("newcomer", duration=9999)
        assert "no history yet, watched" in verdict


class TestWaivers:
    def test_the_unbounded_action_runs_under_its_reason(self):
        built = keeper()
        built.waive("fuzzer", reason="runtime is data-dependent")
        verdict = built.observe_run("fuzzer", duration=99999)
        assert "under waiver (runtime is data-dependent)" in verdict

    def test_reasonless_waivers_are_refused(self):
        with pytest.raises(Invalid, match="nobody chose"):
            keeper().waive("x", reason="  ")

    def test_the_report_separates_the_three_columns(self):
        built = keeper()
        built.waive("fuzzer", reason="data-dependent")
        built.observe_run("long_link", duration=100)
        built.observe_run("quick_lint", duration=500)
        built.observe_run("fuzzer", duration=5000)
        assert built.patience_report() == (
            "1 clean, 1 killed, 1 waived across 1 standing waivers"
        )
