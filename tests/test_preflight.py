from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.preflight import Preflight


def rigged(parse_error=None, graph_error=None) -> Preflight:
    flight = Preflight()
    flight.add_check("graph", 5, lambda: graph_error)
    flight.add_check("parse", 2, lambda: parse_error)
    return flight


class TestTheOrder:
    def test_checks_run_cheapest_first(self):
        flight = rigged(
            parse_error="unexpected token",
            graph_error="cycle",
        )
        verdict = flight.run()
        assert "CAUGHT AT THE DESK by parse after 2 tick(s)" in (
            verdict
        )

    def test_the_first_failure_stops_the_flight(self):
        flight = rigged(parse_error="unexpected token")
        flight.run()
        assert flight.toll_paid == 2

    def test_a_clean_flight_pays_the_full_toll(self):
        flight = rigged()
        assert flight.run() == "clean after 7 tick(s); submit"
        assert flight.clean_runs == 1

    def test_an_empty_preflight_is_refused(self):
        with pytest.raises(Invalid):
            Preflight().run()

    def test_a_free_check_is_refused(self):
        with pytest.raises(Invalid):
            Preflight().add_check("magic", 0, lambda: None)


class TestTheLedger:
    def test_a_catching_preflight_earns_its_keep(self):
        flight = rigged(parse_error="broken")
        flight.run()
        ledger = flight.ledger()
        assert "banked 90 tick(s) against a toll of 2" in ledger
        assert "earns 88" in ledger

    def test_a_quiet_team_gets_the_honest_verdict(self):
        flight = rigged()
        for _ in range(20):
            flight.run()
        ledger = flight.ledger()
        assert "honest overhead" in ledger
        assert "allowed to say so" in ledger
