from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.fairshare import FairShare


def farm() -> FairShare:
    return FairShare(
        entitlements={"search": 0.5, "ads": 0.3, "infra": 0.2}
    )


class TestAccounting:
    def test_entitlements_must_sum_to_one(self):
        with pytest.raises(Invalid):
            FairShare(entitlements={"a": 0.5, "b": 0.2})

    def test_strangers_cannot_be_charged(self):
        with pytest.raises(Invalid):
            farm().charge("growth", 10)

    def test_an_idle_farm_gives_the_slot_to_the_biggest_share(self):
        assert farm().next_slot() == "search"


class TestFairness:
    def test_the_hog_loses_the_next_slot(self):
        shared = farm()
        shared.charge("search", 900)
        shared.charge("ads", 30)
        shared.charge("infra", 20)
        assert shared.next_slot() != "search"

    def test_the_starved_team_rises_to_the_front(self):
        shared = farm()
        shared.charge("search", 500)
        shared.charge("ads", 300)
        assert shared.next_slot() == "infra"

    def test_decay_forgives_last_months_feast(self):
        shared = farm()
        shared.charge("infra", 1000)
        for _ in range(6):
            shared.decay()
        shared.charge("search", 100)
        shared.charge("ads", 100)
        assert shared.next_slot() == "infra"

    def test_a_team_that_stops_submitting_stops_being_charged(self):
        shared = farm()
        shared.charge("ads", 100)
        before = shared.usage["ads"]
        shared.decay()
        shared.decay()
        assert shared.usage["ads"] == before / 4


class TestTheReport:
    def test_the_report_prints_both_numbers_per_team(self):
        shared = farm()
        shared.charge("search", 800)
        shared.charge("ads", 100)
        shared.charge("infra", 100)
        report = shared.report()
        assert (
            "search: using 80% of an entitled 50% (over)"
        ) in report
        assert "ads: using 10% of an entitled 30% (under)" in report
        assert report.splitlines()[-1].startswith("next slot:")
