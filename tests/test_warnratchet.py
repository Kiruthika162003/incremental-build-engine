from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.warnratchet import WarnRatchet

STOCK = {"legacy.c": 30, "parser.c": 4, "clean.c": 0}


def ratchet() -> WarnRatchet:
    built = WarnRatchet()
    built.record_baseline(dict(STOCK))
    return built


class TestTheBaseline:
    def test_the_stock_is_grandfathered_with_a_count(self):
        built = WarnRatchet()
        verdict = built.record_baseline(dict(STOCK))
        assert verdict.startswith(
            "baseline recorded: 34 warning(s) across 3 file(s)"
        )

    def test_the_baseline_records_once(self):
        with pytest.raises(Invalid):
            ratchet().record_baseline({"x.c": 1})


class TestTheRatchet:
    def test_holding_steady_is_clean(self):
        assert ratchet().check(dict(STOCK)).startswith("clean")

    def test_a_new_warning_is_refused_with_both_numbers(self):
        with pytest.raises(Invalid) as caught:
            ratchet().check(dict(STOCK, **{"parser.c": 5}))
        assert (
            "parser.c: 5 warning(s) against a baseline of 4"
        ) in str(caught.value)

    def test_a_brand_new_file_starts_at_zero_allowed(self):
        with pytest.raises(Invalid) as caught:
            ratchet().check(dict(STOCK, **{"fresh.c": 1}))
        assert "fresh.c: 1 warning(s) against a baseline of 0" in (
            str(caught.value)
        )

    def test_improvement_is_re_recorded_and_kept(self):
        built = ratchet()
        built.check(dict(STOCK, **{"legacy.c": 10}))
        with pytest.raises(Invalid):
            built.check(dict(STOCK, **{"legacy.c": 11}))

    def test_a_deleted_file_forfeits_its_allowance(self):
        built = ratchet()
        observed = {"parser.c": 4, "clean.c": 0}
        built.check(observed)
        with pytest.raises(Invalid):
            built.check(dict(observed, **{"legacy.c": 1}))


class TestTheLeaderboard:
    def test_the_debt_is_somebody_specific(self):
        board = ratchet().leaderboard()
        assert board.startswith("34 warning(s) still owed")
        assert board.splitlines()[1] == "  legacy.c: 30"

    def test_the_paid_board_says_flip_the_switch(self):
        built = WarnRatchet()
        built.record_baseline({"a.c": 0})
        assert built.leaderboard() == (
            "the debt is paid; turn warnings into errors"
        )
