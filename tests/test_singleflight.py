from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.singleflight import SingleFlight

KEY = "compile:core.h-cone"


def storm(size: int) -> SingleFlight:
    flight = SingleFlight()
    flight.request(KEY, "ci-shard-0", run_ticks=90)
    for number in range(1, size):
        flight.request(KEY, f"ci-shard-{number}", run_ticks=90)
    return flight


class TestCoalescing:
    def test_the_first_request_leads(self):
        flight = SingleFlight()
        assert flight.request(KEY, "dev-a", 90) == (
            "dev-a: leader, building"
        )

    def test_duplicates_subscribe_instead_of_spawning(self):
        flight = storm(3)
        assert flight.builds_started == 1
        assert flight.subscriptions == 2

    def test_completion_fans_out_to_every_subscriber(self):
        flight = storm(5)
        verdict = flight.complete(KEY, "digest-77")
        assert verdict == (
            "digest-77 fanned out to 4 subscriber(s)"
        )

    def test_late_requests_are_served_from_the_result(self):
        flight = storm(2)
        flight.complete(KEY, "digest-77")
        assert "served from the finished result" in (
            flight.request(KEY, "late-dev", 90)
        )
        assert flight.builds_started == 1

    def test_a_flightless_completion_is_refused(self):
        with pytest.raises(Invalid):
            SingleFlight().complete("ghost", "d")


class TestTheReceipt:
    def test_the_storm_receipt_prices_the_echo(self):
        flight = storm(400)
        assert flight.receipt() == (
            "1 build(s) for 400 request(s): spent 90 tick(s) "
            "where the echo pays 36000"
        )

    def test_distinct_keys_still_build_independently(self):
        flight = SingleFlight()
        flight.request("k1", "a", 10)
        flight.request("k2", "b", 10)
        assert flight.builds_started == 2
