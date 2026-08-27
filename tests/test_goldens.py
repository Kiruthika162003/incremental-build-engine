from __future__ import annotations

import pytest

from forge.errors import Invalid, Missing
from forge.goldens import GoldenStore

PAGE = "header\nbody line one\nbody line two\n"


def store() -> GoldenStore:
    built = GoldenStore()
    built.record("report.txt", PAGE)
    return built


class TestChecking:
    def test_a_match_is_quiet(self):
        assert store().check("report.txt", PAGE) == (
            "report.txt: matches"
        )

    def test_the_mismatch_names_the_first_line(self):
        verdict = store().check(
            "report.txt", "header\nbody CHANGED\nbody line two\n"
        )
        assert "MISMATCH at line 2" in verdict
        assert "bless with a reason or fix the code" in verdict

    def test_a_longer_actual_diffs_past_the_end(self):
        verdict = store().check("report.txt", PAGE + "extra\n")
        assert "MISMATCH at line 4" in verdict

    def test_an_unknown_golden_is_missing(self):
        with pytest.raises(Missing):
            store().check("ghost.txt", "x")


class TestBlessing:
    def test_a_blessing_carries_its_reason_forward(self):
        chosen = store()
        verdict = chosen.bless(
            "report.txt",
            "header\nnew truth\n",
            reason="the report format gained a version field",
        )
        assert "blessed" in verdict
        assert chosen.reasons["report.txt"] == (
            "the report format gained a version field"
        )
        assert chosen.check(
            "report.txt", "header\nnew truth\n"
        ).endswith("matches")

    def test_a_reasonless_blessing_is_refused(self):
        with pytest.raises(Invalid):
            store().bless("report.txt", "x", reason="  ")

    def test_blessing_a_match_is_refused(self):
        with pytest.raises(Invalid):
            store().bless("report.txt", PAGE, reason="why not")

    def test_rerecording_is_refused(self):
        with pytest.raises(Invalid):
            store().record("report.txt", "again")


class TestTheSessionLedger:
    def test_a_holding_session_reads_clean(self):
        chosen = store()
        chosen.check("report.txt", PAGE)
        assert chosen.session_verdict() == (
            "1 check(s), no blessings; the goldens held"
        )

    def test_bulk_blessing_is_named_a_surrender(self):
        chosen = GoldenStore()
        for number in range(4):
            chosen.record(f"g{number}", "old")
        chosen.check("g0", "old")
        for number in range(4):
            chosen.bless(f"g{number}", "new", reason="mass update")
        assert "surrender with paperwork" in (
            chosen.session_verdict()
        )
