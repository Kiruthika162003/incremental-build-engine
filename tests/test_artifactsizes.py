from __future__ import annotations

import pytest

from forge.artifactsizes import SizeLedger
from forge.errors import Invalid


def ledger() -> SizeLedger:
    built = SizeLedger()
    built.budget("app", ceiling=1000, slope_per_window=50)
    return built


class TestTheCeiling:
    def test_within_budget_reads_plainly(self):
        assert ledger().record("app", "c1", 500) == "within budget"

    def test_crossing_the_ceiling_refuses_the_build(self):
        verdict = ledger().record("app", "c1", 1001)
        assert verdict == (
            "REFUSED: app at 1001 crosses its ceiling of 1000"
        )

    def test_unbudgeted_artifacts_are_refused(self):
        with pytest.raises(Invalid, match="unmeasured growth"):
            SizeLedger().record("mystery", "c1", 10)

    def test_nonsense_budgets_are_refused(self):
        with pytest.raises(Invalid):
            SizeLedger().budget("x", ceiling=0, slope_per_window=1)


class TestTheSlope:
    def test_innocent_commits_add_up_to_a_flag(self):
        built = ledger()
        size = 500
        verdict = "within budget"
        for number in range(6):
            size += 15
            verdict = built.record("app", f"c{number}", size)
        assert verdict.startswith("SLOPE: app grew 75")

    def test_flat_history_never_flags(self):
        built = ledger()
        for number in range(6):
            assert built.record("app", f"c{number}", 500) == (
                "within budget"
            )

    def test_the_window_forgives_ancient_growth(self):
        built = ledger()
        built.record("app", "old", 100)
        for number in range(6):
            verdict = built.record("app", f"c{number}", 500)
        assert verdict == "within budget"


class TestAttribution:
    def test_the_bytes_are_named_to_their_builds(self):
        built = ledger()
        built.record("app", "c1", 500)
        built.record("app", "c2", 540)
        built.record("app", "c3", 540)
        built.record("app", "c4", 560)
        assert built.attribution("app") == [
            "c2 brought 40 bytes",
            "c4 brought 20 bytes",
        ]

    def test_shrinkage_is_not_blamed(self):
        built = ledger()
        built.record("app", "c1", 500)
        built.record("app", "c2", 400)
        assert built.attribution("app") == []

    def test_thin_history_is_refused(self):
        built = ledger()
        built.record("app", "c1", 500)
        with pytest.raises(Invalid, match="too little history"):
            built.attribution("app")
