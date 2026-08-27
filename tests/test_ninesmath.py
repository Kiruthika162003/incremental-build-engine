from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.ninesmath import (
    downtime_minutes_per_year,
    nines_label,
    parallel,
    platform_promise,
    series,
)


class TestTheTable:
    def test_three_nines_is_more_downtime_than_meetings_expect(self):
        assert downtime_minutes_per_year(99.9) == pytest.approx(
            525.96
        )

    def test_availability_is_a_strict_percentage(self):
        with pytest.raises(Invalid):
            downtime_minutes_per_year(100)

    def test_the_label_counts_nines_with_the_bill(self):
        assert nines_label(99.9) == (
            "99.9% is 3 nine(s), 526 minute(s) a year"
        )
        assert nines_label(99.0) == (
            "99.0% is 2 nine(s), 5260 minute(s) a year"
        )
        assert nines_label(90.0) == (
            "90.0% is 1 nine(s), 52596 minute(s) a year"
        )

    def test_eighty_five_has_nothing_to_brag_about(self):
        assert nines_label(85.0) == (
            "85.0% has no nines to brag about"
        )


class TestComposition:
    def test_series_promises_compose_down(self):
        assert series([99.9, 99.9]) == pytest.approx(
            99.8001
        )

    def test_the_three_organ_platform_inherits_the_product(self):
        verdict = platform_promise([99.9, 99.95, 99.9])
        assert verdict.startswith("the platform is 99.75%")
        assert "quoting a component, not a platform" in verdict

    def test_parallel_redundancy_carries_its_honesty_clause(self):
        verdict = parallel([99.0, 99.0])
        assert verdict.startswith("99.9900% assuming independence")
        assert "share a fate" in verdict

    def test_composition_needs_company(self):
        with pytest.raises(Invalid):
            series([99.9])
        with pytest.raises(Invalid):
            parallel([99.9])
