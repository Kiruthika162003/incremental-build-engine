from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.volumepack import (
    comparison_bill,
    naive_pack,
    sorted_pack,
)

NIGHTLY = [30, 20, 15, 60, 70, 45, 10, 55, 25, 40]


class TestTheTwoOrders:
    def test_on_80_unit_volumes_sorting_closes_a_disk(self):
        naive = naive_pack(NIGHTLY, 80)
        clever = sorted_pack(NIGHTLY, 80)
        assert naive.volume_count() == 6
        assert clever.volume_count() == 5
        assert naive.waste() == 110
        assert clever.waste() == 30

    def test_a_forgiving_volume_size_admits_the_tie(self):
        bill = comparison_bill(NIGHTLY, 100)
        assert (
            "this artifact set forgives the naive order" in bill
        )

    def test_the_bill_prints_the_purchase_order(self):
        bill = comparison_bill(NIGHTLY, 80)
        assert (
            "arrival order uses 6 volume(s) wasting 110; "
            "sorted greed uses 5 wasting 30"
        ) in bill
        assert "sorting closed 1 whole volume(s)" in bill
        assert "a purchase order" in bill


class TestRefusals:
    def test_the_oversized_artifact_gets_honest_advice(self):
        with pytest.raises(Invalid) as caught:
            naive_pack([120], 100)
        assert "split it or buy bigger disks" in str(caught.value)

    def test_empty_and_nonpositive_are_refused(self):
        with pytest.raises(Invalid):
            naive_pack([], 100)
        with pytest.raises(Invalid):
            sorted_pack([0], 100)
