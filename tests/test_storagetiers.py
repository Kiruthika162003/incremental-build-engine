from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.storagetiers import (
    StoredArtifact,
    monthly_bill,
    placement_report,
    right_tier,
)

LEGAL_RELEASE = StoredArtifact(
    name="release-2030.4",
    tier="cold",
    size_units=10,
    reads_this_month=5,
)
DEBUG_BUNDLE = StoredArtifact(
    name="debug-bundle-tue",
    tier="hot",
    size_units=50,
    reads_this_month=0,
)
DAILY = StoredArtifact(
    name="nightly-app",
    tier="hot",
    size_units=5,
    reads_this_month=30,
)


class TestTheIdeal:
    def test_access_beats_age(self):
        assert right_tier(5) == "hot"
        assert right_tier(0) == "cold"
        assert right_tier(2) == "nearline"

    def test_bad_artifacts_are_refused(self):
        with pytest.raises(Invalid):
            StoredArtifact(
                name="x", tier="lava", size_units=1,
                reads_this_month=0,
            )
        with pytest.raises(Invalid):
            StoredArtifact(
                name="x", tier="hot", size_units=0,
                reads_this_month=0,
            )


class TestTheBill:
    def test_the_bill_is_rent_plus_latency(self):
        assert monthly_bill(DAILY) == 10 * 5 + 1 * 30
        assert monthly_bill(LEGAL_RELEASE) == 1 * 10 + 5000 * 5


class TestTheReport:
    def test_both_waste_directions_are_kept_apart(self):
        report = placement_report(
            [LEGAL_RELEASE, DEBUG_BUNDLE, DAILY]
        )
        assert report.startswith(
            "1 placed well, 1 hot-hoarding, 1 cold-thrashing"
        )
        assert "hoarding (wastes money quietly):" in report
        assert (
            "debug-bundle-tue: hot -> cold saves 450/month"
        ) in report
        assert "thrashing (wastes people loudly):" in report
        assert (
            "release-2030.4: cold -> hot saves 24905/month"
        ) in report

    def test_an_empty_store_is_refused(self):
        with pytest.raises(Invalid):
            placement_report([])
