from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.pagebudget import PageBudget


def noisy_week() -> PageBudget:
    budget = PageBudget(weekly_cap=6)
    for number in range(8):
        budget.raise_alert(
            "flaky-disk-monitor", "warning", f"disk blip {number}"
        )
    budget.raise_alert(
        "cache-corruption", "critical", "digest mismatch"
    )
    budget.raise_alert("deploy-bot", "info", "rollout done")
    return budget


class TestTheCap:
    def test_severity_spends_first_and_overflow_demotes(self):
        budget = noisy_week()
        verdict = budget.flush_week()
        assert verdict.startswith(
            "6 paged, 4 demoted to the daily digest"
        )
        assert "counted, not dropped" in verdict
        assert budget.paged[0] == (
            "cache-corruption", "digest mismatch"
        )

    def test_a_quiet_week_pages_everything(self):
        budget = PageBudget(weekly_cap=10)
        budget.raise_alert("cache", "critical", "x")
        assert budget.flush_week() == (
            "1 paged, 0 demoted to the daily digest"
        )

    def test_a_zero_cap_is_a_blindfold(self):
        with pytest.raises(Invalid):
            PageBudget(weekly_cap=0)

    def test_unknown_severities_are_refused(self):
        with pytest.raises(Invalid):
            noisy_week().raise_alert("x", "loud", "m")


class TestTheLedger:
    def test_the_flaky_monitor_is_named_with_its_share(self):
        budget = noisy_week()
        budget.flush_week()
        ledger = budget.spend_ledger()
        assert (
            "flaky-disk-monitor: 5 page(s) (83% of the budget)"
        ) in ledger
        assert "fix the monitor, not the cap" in ledger

    def test_an_empty_window_has_no_ledger(self):
        with pytest.raises(Invalid):
            PageBudget(weekly_cap=3).spend_ledger()
