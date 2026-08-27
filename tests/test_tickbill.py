from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.tickbill import ClassBill, compare_months

MAY = {
    "compile": ClassBill("compile", actions=200, total_ticks=2000),
    "link": ClassBill("link", actions=10, total_ticks=400),
    "test": ClassBill("test", actions=100, total_ticks=1000),
}
JUNE = {
    "compile": ClassBill("compile", actions=220, total_ticks=2860),
    "link": ClassBill("link", actions=10, total_ticks=400),
    "test": ClassBill("test", actions=90, total_ticks=900),
}


class TestTheSplit:
    def test_volume_and_unit_cost_are_separated(self):
        report = compare_months(MAY, JUNE)
        assert (
            "debit compile: +860 (volume +200, unit cost +660)"
        ) in report

    def test_shrinking_classes_are_credits_not_silence(self):
        report = compare_months(MAY, JUNE)
        assert "credit test: -100" in report

    def test_the_flat_class_stays_off_the_bill(self):
        assert "link" not in compare_months(MAY, JUNE)

    def test_the_growth_gets_an_address_with_its_share(self):
        report = compare_months(MAY, JUNE)
        assert report.startswith("3400 -> 4160 tick(s) (+22%)")
        assert (
            "the growth has an address: compile carries 113% "
            "of it"
        ) in report

    def test_a_new_class_is_named_not_split(self):
        after = dict(JUNE)
        after["codegen"] = ClassBill(
            "codegen", actions=5, total_ticks=50
        )
        assert (
            "debit codegen: +50 (new or retired class)"
        ) in compare_months(MAY, after)


class TestRefusals:
    def test_empty_months_are_refused(self):
        with pytest.raises(Invalid):
            compare_months({}, JUNE)

    def test_ticks_without_actions_are_refused(self):
        with pytest.raises(Invalid):
            ClassBill("odd", actions=0, total_ticks=5).unit_cost()
