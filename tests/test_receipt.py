from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.receipt import BuildFacts, receipt


def facts(**overrides) -> BuildFacts:
    settings = {
        "targets_ran": 4,
        "cache_hits": 12,
        "cutoff_skips": 3,
        "interface_skips": 5,
        "farm_ticks": 120,
        "developer_wait_ticks": 8,
    }
    settings.update(overrides)
    return BuildFacts(**settings)


class TestTheReceipt:
    def test_the_three_owned_numbers_lead(self):
        page = receipt(facts())
        assert page.startswith("ran 4, avoided 20")
        assert (
            "saved by: cache 12, early cutoff 3, "
            "interface cutoff 5"
        ) in page

    def test_the_farm_sentence_builds_trust(self):
        assert (
            "the farm paid 120 tick(s) so you waited 8"
        ) in receipt(facts())

    def test_zero_line_items_stay_off_the_receipt(self):
        page = receipt(
            facts(cutoff_skips=0, interface_skips=0)
        )
        assert "early cutoff" not in page
        assert "saved by: cache 12" in page

    def test_a_local_build_says_so(self):
        page = receipt(
            facts(farm_ticks=0, developer_wait_ticks=15)
        )
        assert "everything local: you waited 15 tick(s)" in page


class TestHonesty:
    def test_a_lying_clock_is_refused(self):
        with pytest.raises(Invalid) as caught:
            facts(developer_wait_ticks=500)
        assert "someone's clock is lying" in str(caught.value)

    def test_a_build_that_did_nothing_did_not_happen(self):
        with pytest.raises(Invalid):
            receipt(
                facts(
                    targets_ran=0,
                    cache_hits=0,
                    cutoff_skips=0,
                    interface_skips=0,
                )
            )

    def test_negative_numbers_are_refused(self):
        with pytest.raises(Invalid):
            facts(cache_hits=-1)
