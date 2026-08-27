from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.shadowbuild import MigrationRatchet, ShadowRun

OLD = {
    "bin/app": "d1",
    "bin/tool": "d2",
    "lib/core.a": "d3",
    "docs/man.1": "d4",
}


def mostly_agreeing() -> ShadowRun:
    return ShadowRun(
        old_outputs=dict(OLD),
        new_outputs={
            "bin/app": "d1",
            "bin/tool": "WRONG",
            "lib/core.a": "d3",
            "stamp.json": "s1",
        },
    )


class TestTriage:
    def test_the_three_disagreement_kinds_are_kept_apart(self):
        run = mostly_agreeing()
        assert run.miscompiles() == ["bin/tool"]
        assert run.gaps() == ["docs/man.1"]
        assert run.extras() == ["stamp.json"]

    def test_agreement_is_measured_against_the_old_system(self):
        assert mostly_agreeing().agreement_percent() == 50

    def test_the_triage_report_orders_the_work(self):
        report = mostly_agreeing().triage()
        assert report.startswith("agreement 50% (2 of 4 outputs)")
        assert "differ (fix these first): bin/tool" in report
        assert "only the old system builds: docs/man.1" in report
        assert "stamps to allowlist): stamp.json" in report

    def test_full_agreement_says_cut_over(self):
        run = ShadowRun(
            old_outputs=dict(OLD), new_outputs=dict(OLD)
        )
        assert "the shadow is the system; cut over" in run.triage()

    def test_an_empty_baseline_is_refused(self):
        with pytest.raises(Invalid):
            ShadowRun(
                old_outputs={}, new_outputs={"x": "d"}
            ).agreement_percent()


class TestTheRatchet:
    def test_the_ratchet_counts_gains(self):
        ratchet = MigrationRatchet()
        verdict = ratchet.advance(mostly_agreeing())
        assert "ratchet advances: 2 new agreement(s)" in verdict
        assert ratchet.agreed == {"bin/app", "lib/core.a"}

    def test_lost_ground_is_a_named_regression(self):
        ratchet = MigrationRatchet()
        ratchet.advance(mostly_agreeing())
        worse = ShadowRun(
            old_outputs=dict(OLD),
            new_outputs={"bin/app": "BROKEN", "lib/core.a": "d3"},
        )
        verdict = ratchet.advance(worse)
        assert verdict.startswith("REGRESSION: bin/app")
        assert ratchet.regressions == ["bin/app"]

    def test_a_quiet_run_holds_the_line(self):
        ratchet = MigrationRatchet()
        ratchet.advance(mostly_agreeing())
        assert ratchet.advance(mostly_agreeing()) == (
            "holding at 2 agreement(s)"
        )
