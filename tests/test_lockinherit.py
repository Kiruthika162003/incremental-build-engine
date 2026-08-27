from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.lockinherit import (
    Contention,
    LockLedger,
    comparison,
    wait_with_inheritance,
    wait_without_inheritance,
)

RELEASE_NIGHT = Contention(
    holder_ticks_left=8,
    parade_jobs=12,
    parade_ticks_each=15,
)


class TestTheTwoWaits:
    def test_without_inheritance_the_parade_goes_first(self):
        assert wait_without_inheritance(RELEASE_NIGHT) == 188

    def test_with_inheritance_only_the_lock_remains(self):
        assert wait_with_inheritance(RELEASE_NIGHT) == 8

    def test_the_comparison_names_the_gap_correctly(self):
        line = comparison(RELEASE_NIGHT)
        assert (
            "waits 188 tick(s) without inheritance and 8 "
            "with it"
        ) in line
        assert (
            "the 180-tick gap is the width of the parade, "
            "not of the lock"
        ) in line

    def test_an_idle_holder_is_refused(self):
        with pytest.raises(Invalid):
            Contention(
                holder_ticks_left=0,
                parade_jobs=1,
                parade_ticks_each=1,
            )


class TestTheLedger:
    def test_each_inversion_is_narrated(self):
        ledger = LockLedger()
        verdict = ledger.observe(RELEASE_NIGHT)
        assert verdict.startswith("inversion #1")
        assert "returns to obscurity" in verdict

    def test_the_season_totals_the_avoided_parade(self):
        ledger = LockLedger()
        ledger.observe(RELEASE_NIGHT)
        ledger.observe(
            Contention(
                holder_ticks_left=5,
                parade_jobs=2,
                parade_ticks_each=10,
            )
        )
        report = ledger.season_report()
        assert report.startswith(
            "2 inversion(s), 200 parade tick(s) avoided"
        )
        assert "invisible until measured" in report

    def test_a_quiet_season_admits_both_readings(self):
        with pytest.raises(Invalid) as caught:
            LockLedger().season_report()
        assert "or nobody is looking" in str(caught.value)
