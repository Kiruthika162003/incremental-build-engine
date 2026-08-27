from __future__ import annotations

import pytest

from forge.cachetrust import TrustCache, register_trusted
from forge.errors import Invalid


def cache() -> TrustCache:
    built = TrustCache()
    register_trusted(built, "ci-fleet")
    return built


class TestTiers:
    def test_the_ci_fleet_is_believed_outright(self):
        built = cache()
        assert built.upload("k1", "digest-a", "ci-fleet") == "served"
        assert built.lookup("k1") == "digest-a"

    def test_the_laptop_lands_in_quarantine(self):
        built = cache()
        assert built.upload("k1", "digest-a", "laptop-9") == (
            "quarantined"
        )
        assert built.lookup("k1") is None
        assert built.quarantine_refusals == 1

    def test_double_trusting_is_refused(self):
        built = cache()
        with pytest.raises(Invalid):
            register_trusted(built, "ci-fleet")


class TestCorroboration:
    def test_a_second_independent_writer_promotes(self):
        built = cache()
        built.upload("k1", "digest-a", "laptop-9")
        outcome = built.upload("k1", "digest-a", "laptop-3")
        assert outcome == "corroborated and promoted"
        assert built.lookup("k1") == "digest-a"
        assert built.promotions == 1

    def test_the_same_writer_twice_is_not_corroboration(self):
        built = cache()
        built.upload("k1", "digest-a", "laptop-9")
        assert built.upload("k1", "digest-a", "laptop-9") == (
            "already known"
        )
        assert built.lookup("k1") is None


class TestCollisions:
    def test_disagreement_freezes_both_and_names_both(self):
        built = cache()
        built.upload("k1", "digest-a", "laptop-9")
        outcome = built.upload("k1", "digest-b", "laptop-3")
        assert outcome.startswith("COLLISION")
        assert built.lookup("k1") is None
        assert built.collisions == [
            "k1: laptop-9 and laptop-3 disagree; both frozen"
        ]

    def test_a_frozen_key_accepts_nothing(self):
        built = cache()
        built.upload("k1", "digest-a", "laptop-9")
        built.upload("k1", "digest-b", "laptop-3")
        assert built.upload("k1", "digest-a", "ci-fleet") == (
            "k1 is frozen pending investigation"
        )

    def test_the_ledger_shows_its_refusals(self):
        built = cache()
        built.upload("k1", "digest-a", "ci-fleet")
        built.upload("k2", "digest-b", "laptop-9")
        built.lookup("k2")
        built.upload("k3", "digest-c", "laptop-9")
        built.upload("k3", "digest-d", "laptop-3")
        assert built.ledger() == (
            "1 served, 1 in quarantine, 0 promoted by corroboration, "
            "1 quarantine serves refused, 1 collisions frozen"
        )
