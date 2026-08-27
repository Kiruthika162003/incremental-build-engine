from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.tieredcache import TieredCache


def warm_remote() -> TieredCache:
    cache = TieredCache(local_capacity=2)
    cache.remote.update(
        {"k1": "d1", "k2": "d2", "k3": "d3"}
    )
    return cache


class TestTheReadPath:
    def test_the_first_ask_pays_remote_and_promotes(self):
        cache = warm_remote()
        assert cache.lookup("k1") == "d1"
        assert cache.ticks_paid == 25
        assert "k1" in cache.local

    def test_the_second_ask_costs_one_tick(self):
        cache = warm_remote()
        cache.lookup("k1")
        cache.lookup("k1")
        assert cache.ticks_paid == 26

    def test_a_miss_everywhere_still_pays_the_remote_ask(self):
        cache = warm_remote()
        assert cache.lookup("ghost") is None
        assert cache.ticks_paid == 25


class TestEviction:
    def test_lru_evicts_the_coldest_key(self):
        cache = warm_remote()
        cache.lookup("k1")
        cache.lookup("k2")
        cache.lookup("k1")
        cache.lookup("k3")
        assert set(cache.local) == {"k1", "k3"}

    def test_eviction_is_harmless_because_remote_holds_on(self):
        cache = warm_remote()
        cache.lookup("k1")
        cache.lookup("k2")
        cache.lookup("k3")
        assert cache.lookup("k1") == "d1"

    def test_a_zero_slot_local_tier_is_refused(self):
        with pytest.raises(Invalid):
            TieredCache(local_capacity=0)


class TestTheLedger:
    def test_reused_promotions_report_their_saving(self):
        cache = warm_remote()
        cache.lookup("k1")
        cache.lookup("k1")
        cache.lookup("k1")
        assert (
            "1 re-asked saving 24 tick(s), 0 freight paid for "
            "nothing"
        ) in cache.ledger()

    def test_unreused_promotions_are_freight_for_nothing(self):
        cache = warm_remote()
        cache.lookup("k1")
        cache.lookup("k2")
        assert "2 freight paid for nothing" in cache.ledger()

    def test_stores_promote_for_the_builder_own_reuse(self):
        cache = TieredCache(local_capacity=2)
        cache.store("fresh", "d9")
        assert cache.lookup("fresh") == "d9"
        assert cache.ticks_paid == 1
