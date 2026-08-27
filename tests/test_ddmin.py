from __future__ import annotations

import pytest

from forge.ddmin import Minimizer
from forge.errors import Invalid

FLEET = tuple(f"input{number:02}" for number in range(16))


def culprit_pair(inputs: frozenset[str]) -> bool:
    return {"input03", "input11"} <= inputs


def single_culprit(inputs: frozenset[str]) -> bool:
    return "input07" in inputs


class TestMinimization:
    def test_the_single_culprit_is_found_alone(self):
        minimizer = Minimizer(oracle=single_culprit)
        assert minimizer.minimize(FLEET) == ["input07"]

    def test_the_interacting_pair_survives_together(self):
        minimizer = Minimizer(oracle=culprit_pair)
        assert minimizer.minimize(FLEET) == [
            "input03",
            "input11",
        ]

    def test_the_result_is_one_minimal(self):
        minimizer = Minimizer(oracle=culprit_pair)
        found = minimizer.minimize(FLEET)
        for leave_out in found:
            remaining = frozenset(found) - {leave_out}
            assert not culprit_pair(remaining)

    def test_a_healthy_set_is_refused(self):
        minimizer = Minimizer(oracle=lambda _inputs: False)
        with pytest.raises(Invalid):
            minimizer.minimize(FLEET)

    def test_an_empty_set_is_refused(self):
        with pytest.raises(Invalid):
            Minimizer(oracle=single_culprit).minimize(())


class TestTheBill:
    def test_the_bill_prices_the_purchase(self):
        minimizer = Minimizer(oracle=culprit_pair)
        found = minimizer.minimize(FLEET)
        line = minimizer.bill(len(FLEET), len(found))
        assert line.startswith("16 input(s) became 2")
        assert "build(s)" in line

    def test_the_oracle_bill_is_bounded_for_the_easy_case(self):
        minimizer = Minimizer(oracle=single_culprit)
        minimizer.minimize(FLEET)
        assert minimizer.oracle_calls < 20
