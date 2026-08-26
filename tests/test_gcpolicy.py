from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.gcpolicy import EvictingCache


class TestAdmission:
    def test_room_is_respected(self):
        cache = EvictingCache(capacity_bytes=100)
        cache.admit("a", size=60, cost=5, now=0)
        cache.admit("b", size=30, cost=5, now=1)
        assert cache.held_bytes() == 90

    def test_overflow_evicts_down_to_capacity(self):
        cache = EvictingCache(capacity_bytes=100)
        cache.admit("a", size=60, cost=5, now=0)
        cache.admit("b", size=60, cost=5, now=1)
        assert cache.held_bytes() <= 100
        assert len(cache.entries) == 1

    def test_an_oversized_entry_is_refused(self):
        with pytest.raises(Invalid, match="alone exceeds"):
            EvictingCache(capacity_bytes=10).admit(
                "huge", size=11, cost=1, now=0
            )

    def test_unknown_policies_are_refused(self):
        with pytest.raises(Invalid):
            EvictingCache(capacity_bytes=10, policy="magic")


class TestLru:
    def test_the_coldest_entry_goes_first(self):
        cache = EvictingCache(capacity_bytes=100, policy="lru")
        cache.admit("cold", size=50, cost=5, now=0)
        cache.admit("warm", size=50, cost=5, now=5)
        cache.lookup("cold", now=10)
        cache.admit("new", size=50, cost=5, now=20)
        assert "warm" not in cache.entries
        assert "cold" in cache.entries


class TestCostAware:
    def test_cheap_fat_goes_before_dear_lean(self):
        cache = EvictingCache(capacity_bytes=100, policy="cost-aware")
        cache.admit("cheap-fat", size=80, cost=2, now=0)
        cache.admit("dear-lean", size=15, cost=50, now=0)
        cache.admit("new", size=40, cost=10, now=1)
        assert "cheap-fat" not in cache.entries
        assert "dear-lean" in cache.entries


class TestRegret:
    def test_a_miss_on_the_evicted_is_regret(self):
        cache = EvictingCache(capacity_bytes=100)
        cache.admit("a", size=60, cost=5, now=0)
        cache.admit("b", size=60, cost=5, now=1)
        assert not cache.lookup("a", now=2)
        assert cache.regret_misses == 1

    def test_a_miss_on_the_never_seen_is_not_regret(self):
        cache = EvictingCache(capacity_bytes=100)
        assert not cache.lookup("stranger", now=0)
        assert cache.regret_misses == 0

    def test_the_postmortem_reads_the_losing_bet(self):
        cache = EvictingCache(capacity_bytes=100)
        cache.admit("a", size=60, cost=5, now=0)
        cache.admit("b", size=60, cost=5, now=1)
        assert cache.postmortem("a") == (
            "a was forgotten: lru: cold since 0"
        )
        assert cache.postmortem("zz") == (
            "zz was never evicted; it was never here"
        )

    def test_readmission_clears_the_grudge(self):
        cache = EvictingCache(capacity_bytes=100)
        cache.admit("a", size=60, cost=5, now=0)
        cache.admit("b", size=60, cost=5, now=1)
        cache.admit("a", size=60, cost=5, now=2)
        assert cache.lookup("a", now=3)
        assert cache.regret_misses == 0

    def test_the_judgement_counts_only_what_matters(self):
        cache = EvictingCache(capacity_bytes=100)
        cache.admit("a", size=60, cost=5, now=0)
        cache.admit("b", size=60, cost=5, now=1)
        cache.lookup("a", now=2)
        assert cache.judgement() == (
            "1 evictions, 1 regret misses; the policy is judged by "
            "nothing else"
        )
