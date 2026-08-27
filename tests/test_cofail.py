from __future__ import annotations

import pytest

from forge.cofail import CoFailLedger
from forge.errors import Invalid


def seasoned() -> CoFailLedger:
    ledger = CoFailLedger()
    ledger.record_run(("parser.c",), ("test_parse", "test_ast"))
    ledger.record_run(("parser.c",), ("test_parse",))
    ledger.record_run(("parser.c", "util.c"), ("test_parse",))
    ledger.record_run(("render.c",), ("test_render",))
    ledger.record_run(("render.c",), ())
    return ledger


class TestTheRecord:
    def test_cofailure_counts_are_conditional_on_the_file(self):
        counts = seasoned().cofailures("parser.c")
        assert counts == {"test_parse": 3, "test_ast": 1}

    def test_selection_needs_the_floor(self):
        assert seasoned().select("parser.c") == ["test_parse"]

    def test_an_editless_run_teaches_nothing(self):
        with pytest.raises(Invalid):
            CoFailLedger().record_run((), ("t",))


class TestRecall:
    def test_recall_is_scored_against_the_record_itself(self):
        verdict = seasoned().recall("parser.c")
        assert verdict == (
            "parser.c: history selects 1 test(s), catching 3 "
            "of 3 failing run(s) (100% recall on the record)"
        )

    def test_a_quiet_file_cannot_be_scored(self):
        ledger = seasoned()
        ledger.record_run(("quiet.c",), ())
        with pytest.raises(Invalid):
            ledger.recall("quiet.c")


class TestFlakes:
    def test_the_evenly_spread_test_is_a_suspect(self):
        ledger = seasoned()
        for path in ("a.c", "b.c", "c.c"):
            ledger.record_run((path,), ("test_wifi",))
        suspects = ledger.flake_suspects()
        assert len(suspects) == 1
        assert suspects[0].startswith(
            "test_wifi: fails alongside 3 different file(s)"
        )
        assert "flake profile, not coupling" in suspects[0]

    def test_a_coupled_test_is_not_accused(self):
        assert seasoned().flake_suspects() == []
