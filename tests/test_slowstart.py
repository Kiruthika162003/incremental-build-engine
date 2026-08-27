from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.slowstart import SlowStart


def ramp() -> SlowStart:
    return SlowStart(full_load=32)


class TestTheRamp:
    def test_clean_rounds_double_to_full_load(self):
        chosen = ramp()
        for _ in range(5):
            chosen.round_result(clean=True)
        assert chosen.allowance == 32
        assert "at full load (32)" in chosen.round_result(
            clean=True
        )

    def test_a_failure_halves_and_holds(self):
        chosen = ramp()
        for _ in range(3):
            chosen.round_result(clean=True)
        verdict = chosen.round_result(clean=False)
        assert "failure at allowance 8; halved to 4" in verdict
        held = chosen.round_result(clean=True)
        assert "held at 4 (penalty round)" in held
        assert "doubles to 8" in chosen.round_result(clean=True)

    def test_the_sick_machine_converges_to_a_trickle(self):
        chosen = ramp()
        for _ in range(6):
            chosen.round_result(clean=False)
        assert chosen.allowance == 1

    def test_a_loadless_ramp_is_refused(self):
        with pytest.raises(Invalid):
            SlowStart(full_load=0)


class TestTheReport:
    def test_the_shape_and_the_blast_radius_are_recorded(self):
        chosen = ramp()
        chosen.round_result(clean=True)
        chosen.round_result(clean=True)
        chosen.round_result(clean=False)
        report = chosen.ramp_report()
        assert report.startswith("ramp 1 -> 2 -> 4")
        assert "1 failure(s) absorbed at reduced blast radius" in (
            report
        )
        assert "not yet believed" in report

    def test_the_full_ramp_reports_its_speed(self):
        chosen = ramp()
        for _ in range(6):
            chosen.round_result(clean=True)
        assert "full load in 6 round(s)" in chosen.ramp_report()

    def test_an_unrun_ramp_has_no_report(self):
        with pytest.raises(Invalid):
            ramp().ramp_report()
