from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.leaselock import LeaseStore


def store() -> LeaseStore:
    built = LeaseStore()
    built.acquire("coord-a", now=0)
    return built


class TestTheLease:
    def test_a_held_lease_makes_candidates_wait(self):
        chosen = store()
        with pytest.raises(Invalid) as caught:
            chosen.acquire("coord-b", now=10)
        assert "coord-b waits" in str(caught.value)

    def test_expiry_transfers_leadership_with_a_new_token(self):
        chosen = store()
        verdict = chosen.acquire("coord-b", now=31)
        assert verdict == (
            "coord-b leads with token 2 until 61"
        )

    def test_renewal_extends_only_before_the_clock(self):
        chosen = store()
        assert chosen.renew("coord-a", now=20) == (
            "coord-a renewed until 50"
        )
        with pytest.raises(Invalid) as caught:
            chosen.renew("coord-a", now=55)
        assert "lost by clock, not courtesy" in str(caught.value)

    def test_a_stranger_cannot_renew(self):
        with pytest.raises(Invalid):
            store().renew("coord-b", now=5)


class TestTheFence:
    def test_current_tokens_write_freely(self):
        chosen = store()
        assert chosen.write("coord-a", 1, "state-v1") == (
            "state-v1 written under token 1"
        )

    def test_the_woken_old_leader_bounces_off_the_fence(self):
        chosen = store()
        chosen.write("coord-a", 1, "state-v1")
        chosen.acquire("coord-b", now=31)
        chosen.write("coord-b", 2, "state-v2")
        with pytest.raises(Invalid) as caught:
            chosen.write("coord-a", 1, "stale-state")
        assert "woke up still believing" in str(caught.value)
        assert "bounces off the fence" in str(caught.value)

    def test_the_incident_summary_prices_the_design(self):
        chosen = store()
        chosen.write("coord-a", 1, "v1")
        chosen.acquire("coord-b", now=31)
        chosen.write("coord-b", 2, "v2")
        with pytest.raises(Invalid):
            chosen.write("coord-a", 1, "stale")
        assert (
            "1 split-brain write(s) converted from corruption "
            "into log lines"
        ) in chosen.incident_summary()

    def test_a_quiet_store_admits_both_readings(self):
        assert "either no split brain, or nobody wrote" in (
            store().incident_summary()
        )
