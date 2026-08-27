from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.shardtests import drifted_scales, pack, round_robin

DURATIONS = {
    "test_slow": 40,
    "test_medium_a": 20,
    "test_medium_b": 20,
    "test_quick_a": 5,
    "test_quick_b": 5,
    "test_quick_c": 5,
    "test_quick_d": 5,
}


class TestPacking:
    def test_greedy_balances_the_shards(self):
        plan = pack(dict(DURATIONS), shard_count=2)
        assert plan.wall_clock() == 50
        assert plan.skew() == 0.0

    def test_the_longest_test_anchors_its_own_shard(self):
        plan = pack(dict(DURATIONS), shard_count=2)
        anchored = next(
            shard for shard in plan.shards if "test_slow" in shard
        )
        assert sum(DURATIONS[name] for name in anchored) == 50

    def test_round_robin_loses_the_comparison(self):
        greedy = pack(dict(DURATIONS), shard_count=2)
        naive = round_robin(dict(DURATIONS), shard_count=2)
        assert naive.wall_clock() > greedy.wall_clock()

    def test_the_line_reads_the_plan(self):
        plan = pack(dict(DURATIONS), shard_count=2)
        assert plan.line() == (
            "2 shards, wall clock 50, skew 0.0%"
        )

    def test_more_shards_than_tests_still_works(self):
        plan = pack({"only": 10}, shard_count=4)
        assert plan.wall_clock() == 10

    def test_nonsense_inputs_are_refused(self):
        with pytest.raises(Invalid):
            pack({}, shard_count=2)
        with pytest.raises(Invalid):
            pack({"a": 1}, shard_count=0)
        with pytest.raises(Invalid):
            pack({"a": -1}, shard_count=1)


class TestDrift:
    def test_the_grown_test_is_named_with_both_numbers(self):
        drifted = drifted_scales(
            recorded={"test_slow": 40, "test_quick_a": 5},
            observed={"test_slow": 130, "test_quick_a": 6},
        )
        assert drifted == ["test_slow: recorded 40, observed 130"]

    def test_shrinkage_drifts_too(self):
        drifted = drifted_scales(
            recorded={"test_slow": 40},
            observed={"test_slow": 10},
        )
        assert len(drifted) == 1

    def test_the_unobserved_are_not_accused(self):
        assert drifted_scales(
            recorded={"test_gone": 40}, observed={}
        ) == []
