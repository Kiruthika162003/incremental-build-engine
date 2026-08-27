from __future__ import annotations

import pytest

from forge.actions import Action
from forge.cache import ActionCache
from forge.errors import Invalid
from forge.uncachetag import ExemptionLedger, NoCacheTag
from forge.workspace import Workspace


def fetch_rates(runs: list[int]) -> Action:
    def rule(view) -> None:
        runs[0] += 1
        view.write_text("rates.json", f"rates run {runs[0]}")

    return Action(
        name="fetch-rates",
        command="curl rates",
        reads=(),
        writes=("rates.json",),
        rule=rule,
    )


def world() -> Workspace:
    return Workspace()


class TestTags:
    def test_a_reasonless_exemption_is_refused(self):
        with pytest.raises(Invalid, match="paperwork"):
            NoCacheTag(rule="fetch-rates", reason="   ", cost=2)

    def test_double_exemption_is_refused(self):
        ledger = ExemptionLedger(budget_ticks=10)
        tag = NoCacheTag(
            rule="fetch-rates", reason="talks to the network", cost=2
        )
        ledger.declare(tag)
        with pytest.raises(Invalid, match="already exempt"):
            ledger.declare(tag)

    def test_the_budget_caps_the_exemption_list(self):
        ledger = ExemptionLedger(budget_ticks=3)
        ledger.declare(
            NoCacheTag(rule="a", reason="network", cost=2)
        )
        with pytest.raises(Invalid, match="decoration"):
            ledger.declare(
                NoCacheTag(rule="b", reason="network", cost=2)
            )


class TestForcedRuns:
    def test_the_exempt_rule_runs_every_build(self):
        runs = [0]
        ledger = ExemptionLedger(budget_ticks=10)
        ledger.declare(
            NoCacheTag(
                rule="fetch-rates", reason="live data", cost=2
            )
        )
        cache = ActionCache()
        tree = world()
        action = fetch_rates(runs)
        assert ledger.run(action, cache, tree) == "forced"
        assert ledger.run(action, cache, tree) == "forced"
        assert runs == [2]
        assert cache.entries == {}

    def test_untagged_rules_still_answer_to_the_cache(self):
        runs = [0]
        ledger = ExemptionLedger(budget_ticks=10)
        cache = ActionCache()
        tree = world()
        action = fetch_rates(runs)
        assert ledger.run(action, cache, tree) == "miss"
        assert ledger.run(action, cache, tree) == "hit"
        assert runs == [1]

    def test_the_review_page_orders_by_cost(self):
        ledger = ExemptionLedger(budget_ticks=20)
        ledger.declare(
            NoCacheTag(rule="cheap", reason="clock", cost=1)
        )
        ledger.declare(
            NoCacheTag(rule="dear", reason="license server", cost=9)
        )
        page = ledger.review_page()
        lines = page.splitlines()
        assert lines[0].startswith("dear: 9 ticks")
        assert lines[-1] == (
            "10 of 20 exemption ticks spent, 0 forced runs so far"
        )

    def test_an_empty_ledger_reads_clean(self):
        assert ExemptionLedger(budget_ticks=5).review_page() == (
            "no exemptions; every rule answers to the cache"
        )
