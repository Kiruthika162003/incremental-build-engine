from __future__ import annotations

import pytest

from forge.errorbudget import ErrorBudget
from forge.errors import Invalid


def budget() -> ErrorBudget:
    return ErrorBudget(window_builds=10000, promise_percent=99.0)


class TestTheBudget:
    def test_one_percent_of_the_window_is_spendable(self):
        assert budget().total_budget() == 100

    def test_users_red_tests_never_touch_it(self):
        with pytest.raises(Invalid) as caught:
            budget().burn("user-test-failure", 5)
        assert "learns to fear its users" in str(caught.value)

    def test_burns_report_the_remaining_balance(self):
        chosen = budget()
        verdict = chosen.burn("worker-death", 30)
        assert verdict == (
            "30 burned on worker-death, 70 of 100 left"
        )

    def test_overspending_freezes_the_platform(self):
        chosen = budget()
        chosen.burn("worker-death", 90)
        verdict = chosen.burn("queue-timeout", 20)
        assert verdict.startswith(
            "FROZEN: the budget is overspent by 10"
        )

    def test_a_thin_window_is_refused(self):
        with pytest.raises(Invalid):
            ErrorBudget(window_builds=50, promise_percent=99.0)


class TestTheWindowReport:
    def test_the_burn_gets_a_category_breakdown(self):
        chosen = budget()
        chosen.burn("worker-death", 60)
        chosen.burn("cache-corruption", 20)
        report = chosen.window_report()
        assert report.startswith("window closed: 80 of 100 spent")
        assert "worker-death: 60 (75%)" in report
        assert (
            "worker-death took over half the budget: not bad "
            "luck, a named project nobody has staffed yet"
        ) in report

    def test_the_unspent_budget_is_its_own_finding(self):
        chosen = budget()
        chosen.burn("network", 10)
        assert (
            "the budget went home unspent: the platform moved "
            "slower than its own promise allowed"
        ) in chosen.window_report()
