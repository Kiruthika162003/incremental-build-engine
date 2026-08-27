from __future__ import annotations

import pytest

from forge.controlgroup import ControlGroup
from forge.errors import Invalid


def group() -> ControlGroup:
    return ControlGroup(control_percent=10)


class TestTheSlice:
    def test_the_slice_is_deterministic(self):
        assert group().is_control("build-0")
        assert group().is_control("build-3")
        assert not group().is_control("build-1")

    def test_a_lifestyle_sized_control_is_refused(self):
        with pytest.raises(Invalid):
            ControlGroup(control_percent=80)


class TestRecording:
    def test_control_builds_run_cold_by_design(self):
        chosen = group()
        verdict = chosen.record_build(
            "build-0", 90, "digest-a", key="compile:app"
        )
        assert verdict == "build-0: control, cold by design"
        assert chosen.control_ticks == [90]

    def test_agreeing_cached_builds_pass_quietly(self):
        chosen = group()
        chosen.record_build("build-0", 90, "digest-a", "k")
        assert chosen.record_build(
            "build-1", 8, "digest-a", "k"
        ) == "build-1: cached"

    def test_fast_and_wrong_is_named_with_the_key(self):
        chosen = group()
        chosen.record_build("build-0", 90, "truth-bytes", "k")
        verdict = chosen.record_build(
            "build-1", 8, "stale-bytes", "k"
        )
        assert verdict.startswith("FAST AND WRONG: k")
        assert chosen.disagreements


class TestTheReport:
    def test_the_speedup_is_measured_not_assumed(self):
        chosen = group()
        chosen.record_build("build-0", 90, "d", "k1")
        chosen.record_build("build-3", 110, "d", "k2")
        chosen.record_build("build-1", 8, "d", "k3")
        chosen.record_build("build-2", 12, "d", "k4")
        report = chosen.speedup_report()
        assert report.startswith(
            "measured speedup 10.0x (100 cold against 10 cached)"
        )
        assert "200 control tick(s)" in report

    def test_a_catch_repays_every_tick(self):
        chosen = group()
        chosen.record_build("build-0", 90, "truth", "k")
        chosen.record_build("build-1", 8, "lie", "k")
        assert "repays every tick" in chosen.speedup_report()

    def test_one_population_cannot_make_a_ratio(self):
        chosen = group()
        chosen.record_build("build-0", 90, "d", "k")
        with pytest.raises(Invalid):
            chosen.speedup_report()
