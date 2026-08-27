from __future__ import annotations

import pytest

from forge.diskledger import DiskLedger
from forge.errors import Invalid


def tree() -> DiskLedger:
    ledger = DiskLedger()
    ledger.record("out/app", rule="app", size=500)
    ledger.record("out/app.map", rule="app", size=200)
    ledger.record("out/old_tool", rule="retired_tool", size=900)
    ledger.mark_reachable({"app"})
    return ledger


class TestAttribution:
    def test_orphans_are_the_only_safe_reclaim(self):
        advice = tree().reclaim_advice()
        assert advice.startswith("reclaim 900 bytes safely")
        assert "out/old_tool" in advice
        assert "700 are load-bearing" in advice

    def test_a_clean_tree_reclaims_nothing(self):
        ledger = DiskLedger()
        ledger.record("out/app", rule="app", size=500)
        ledger.mark_reachable({"app"})
        assert ledger.reclaim_advice() == (
            "nothing to reclaim; all 500 bytes are load-bearing"
        )

    def test_negative_bytes_are_refused(self):
        with pytest.raises(Invalid):
            DiskLedger().record("x", rule="r", size=-1)


class TestConsumers:
    def test_the_table_is_per_rule_not_per_directory(self):
        ranked = tree().top_consumers()
        assert ranked[0] == ("retired_tool", 900)
        assert ranked[1] == ("app", 700)

    def test_top_limits_the_table(self):
        assert len(tree().top_consumers(top=1)) == 1


class TestTrends:
    def test_the_doubled_rule_is_more_interesting_than_the_big_one(self):
        ledger = tree()
        ledger.snapshot()
        ledger.record("out/app.debug", rule="app", size=800)
        trends = ledger.trends()
        assert trends == [
            "app: 700 -> 1500 bytes; doubled since the snapshot"
        ]

    def test_steady_rules_stay_out_of_the_news(self):
        ledger = tree()
        ledger.snapshot()
        ledger.record("out/app.extra", rule="app", size=100)
        assert ledger.trends() == []

    def test_trending_without_a_snapshot_is_refused(self):
        with pytest.raises(Invalid):
            tree().trends()
