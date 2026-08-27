from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.shipgate import ShipGate


def gate(budget_clear: bool = True) -> ShipGate:
    built = ShipGate()
    built.report("audits", True, "20 audits, 0 broken")
    built.report(
        "errorbudget",
        budget_clear,
        "70 of 100 spent"
        if budget_clear
        else "FROZEN, overspent by 10",
    )
    built.report(
        "cleanroom", True, "trust renewed, 3 clean nights"
    )
    return built


class TestReporting:
    def test_verdicts_do_not_get_second_drafts(self):
        chosen = gate()
        with pytest.raises(Invalid):
            chosen.report("audits", True, "again")

    def test_a_lightless_gate_reads_sentences_only(self):
        with pytest.raises(Invalid) as caught:
            ShipGate().report("audits", True, "  ")
        assert "the gate does not read lights" in str(
            caught.value
        )

    def test_a_gate_that_asks_almost_nobody_is_a_formality(self):
        chosen = ShipGate()
        chosen.report("audits", True, "clean")
        with pytest.raises(Invalid) as caught:
            chosen.decide()
        assert "a formality" in str(caught.value)


class TestTheDecision:
    def test_go_is_deliberately_underwhelming(self):
        verdict = gate().decide()
        assert verdict.startswith(
            "GO (audits, cleanroom, errorbudget)"
        )
        assert "exists to make it boring" in verdict

    def test_every_no_wears_a_name(self):
        verdict = gate(budget_clear=False).decide()
        assert verdict.startswith(
            "NO-GO: 1 blocker(s), each wearing a name"
        )
        assert (
            "errorbudget: FROZEN, overspent by 10" in verdict
        )
        assert (
            "the meeting starts at the fix, not at the "
            "diagnosis"
        ) in verdict
