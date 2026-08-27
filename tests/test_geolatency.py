from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.geolatency import Office, tax_report

UPSTAIRS = Office(
    name="hq-floor-2", round_trip_ms=2, daily_misses=5000
)
SYDNEY = Office(
    name="sydney", round_trip_ms=300, daily_misses=4000
)


class TestTheTax:
    def test_the_tax_is_trips_times_misses(self):
        assert SYDNEY.daily_tax_ms() == 1_200_000
        assert UPSTAIRS.daily_tax_ms() == 10_000

    def test_an_office_inside_the_farm_is_refused(self):
        with pytest.raises(Invalid):
            Office(name="odd", round_trip_ms=0, daily_misses=1)


class TestTheReport:
    def test_the_heaviest_taxed_office_leads(self):
        report = tax_report([UPSTAIRS, SYDNEY])
        lines = report.splitlines()
        assert lines[1] == (
            "  sydney: 300ms x 4000 miss(es) = 1200000ms/day"
        )

    def test_the_edge_cache_prints_its_payback_in_days(self):
        report = tax_report([UPSTAIRS, SYDNEY])
        assert (
            "earns an edge cache: payback in 41 day(s)"
        ) in report

    def test_the_cheap_office_earns_nothing_extra(self):
        report = tax_report([UPSTAIRS])
        assert "earns an edge cache" not in report

    def test_the_refusal_to_average_is_stated(self):
        assert "erases exactly the person" in tax_report(
            [UPSTAIRS, SYDNEY]
        )

    def test_no_offices_is_refused(self):
        with pytest.raises(Invalid):
            tax_report([])
