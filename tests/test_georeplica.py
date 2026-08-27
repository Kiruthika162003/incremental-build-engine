from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.georeplica import GeoCache


def cache() -> GeoCache:
    built = GeoCache(replication_lag=30)
    built.upload("compile:app", region="eu", now=100)
    return built


class TestTheThreeStates:
    def test_home_region_reads_its_own_write_at_once(self):
        assert cache().state("compile:app", "eu", now=100) == (
            "present"
        )

    def test_the_far_region_sees_the_transit(self):
        assert cache().state("compile:app", "us", now=110) == (
            "in transit, arrives at 130"
        )

    def test_after_the_lag_both_regions_hold_it(self):
        assert cache().state("compile:app", "us", now=130) == (
            "present"
        )

    def test_a_stranger_key_is_absent(self):
        assert cache().state("ghost", "us", now=999) == "absent"


class TestThePolicyKnob:
    def test_interactive_rebuilds_rather_than_waits(self):
        chosen = cache()
        verdict = chosen.lookup(
            "compile:app", "us", now=110, caller="interactive"
        )
        assert "rebuild locally" in verdict
        assert "seconds outrank freight" in verdict
        assert chosen.rebuilds_triggered == 1

    def test_release_waits_for_identity(self):
        chosen = cache()
        verdict = chosen.lookup(
            "compile:app", "us", now=110, caller="release"
        )
        assert "waits until 130" in verdict
        assert "forfeits the identity" in verdict
        assert chosen.waits_served == 1

    def test_a_true_miss_rebuilds_for_everyone(self):
        chosen = cache()
        verdict = chosen.lookup(
            "ghost", "us", now=110, caller="release"
        )
        assert "true miss" in verdict

    def test_an_unknown_caller_class_is_refused(self):
        with pytest.raises(Invalid):
            cache().lookup("compile:app", "us", 110, "cron")

    def test_negative_lag_is_refused(self):
        with pytest.raises(Invalid):
            GeoCache(replication_lag=-1)


class TestTheLedger:
    def test_both_currencies_are_counted(self):
        chosen = cache()
        chosen.lookup("compile:app", "us", 110, "interactive")
        chosen.lookup("compile:app", "us", 111, "release")
        assert chosen.ledger() == (
            "1 rebuild(s) triggered, 1 wait(s) served"
        )
