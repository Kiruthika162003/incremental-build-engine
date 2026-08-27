from __future__ import annotations

import pytest

from forge.crashonly import Component, fleet_audit, grade
from forge.errors import Invalid

JOURNALED = Component(
    name="engine-state",
    recovery_mechanism="journal-replay",
    shutdown_hook_does="hurry",
)
POLITE_ONLY = Component(
    name="stats-flusher",
    recovery_mechanism=None,
    shutdown_hook_does="flush counters to disk",
)
SNEAKY = Component(
    name="lease-holder",
    recovery_mechanism="idempotent-replay",
    shutdown_hook_does="release the lease",
)


class TestGrading:
    def test_the_journaled_component_is_crash_safe(self):
        assert grade(JOURNALED) == (
            "engine-state: crash-safe via journal-replay"
        )

    def test_graceful_only_names_what_the_cord_skips(self):
        verdict = grade(POLITE_ONLY)
        assert verdict.startswith("stats-flusher: GRACEFUL-ONLY")
        assert "the power cord does not call hooks" in verdict

    def test_the_correctness_hook_is_flagged_even_when_safe(self):
        verdict = grade(SNEAKY)
        assert "crash-safe via idempotent-replay" in verdict
        assert "FLAG: its hook does 'release the lease'" in (
            verdict
        )
        assert "after the crash that skipped it" in verdict

    def test_an_unknown_mechanism_is_refused(self):
        with pytest.raises(Invalid):
            grade(
                Component(
                    name="x",
                    recovery_mechanism="hope",
                    shutdown_hook_does="nothing",
                )
            )


class TestTheFleet:
    def test_the_audit_counts_all_three_columns(self):
        report = fleet_audit([JOURNALED, POLITE_ONLY, SNEAKY])
        assert report.startswith(
            "2 crash-safe, 1 graceful-only, 1 hook(s) doing "
            "correctness work"
        )

    def test_the_clean_fleet_trusts_the_power_cord(self):
        clean = Component(
            name="cas",
            recovery_mechanism="atomic-rename",
            shutdown_hook_does="nothing",
        )
        report = fleet_audit([clean, JOURNALED])
        assert "the power cord holds no surprises" in report

    def test_an_empty_fleet_is_refused(self):
        with pytest.raises(Invalid):
            fleet_audit([])
