from __future__ import annotations

import pytest

from forge.circuitbreaker import CircuitBreaker
from forge.errors import Invalid


def tripped() -> CircuitBreaker:
    breaker = CircuitBreaker(service="pkg-registry")
    for tick in range(3):
        breaker.call(now=tick, service_up=False)
    return breaker


class TestTripping:
    def test_three_failures_trip_the_breaker(self):
        breaker = CircuitBreaker(service="pkg-registry")
        breaker.call(now=0, service_up=False)
        breaker.call(now=1, service_up=False)
        verdict = breaker.call(now=2, service_up=False)
        assert "tripped the breaker after 3 failure(s)" in verdict

    def test_a_success_resets_the_count(self):
        breaker = CircuitBreaker(service="pkg-registry")
        breaker.call(now=0, service_up=False)
        breaker.call(now=1, service_up=True)
        breaker.call(now=2, service_up=False)
        assert breaker.state == "closed"


class TestTheOpenState:
    def test_open_refuses_instantly_with_the_reason(self):
        breaker = tripped()
        verdict = breaker.call(now=10, service_up=False)
        assert "refused instantly" in verdict
        assert breaker.fast_fails == 1

    def test_the_cooldown_buys_one_probe(self):
        breaker = tripped()
        verdict = breaker.call(now=60, service_up=True)
        assert "probe succeeded" in verdict
        assert breaker.state == "closed"

    def test_a_failed_probe_reopens_with_a_fresh_clock(self):
        breaker = tripped()
        breaker.call(now=60, service_up=False)
        assert breaker.state == "open"
        verdict = breaker.call(now=70, service_up=True)
        assert "refused instantly" in verdict


class TestTheLedger:
    def test_the_episode_is_priced_in_saved_timeouts(self):
        breaker = tripped()
        for tick in range(10, 14):
            breaker.call(now=tick, service_up=False)
        breaker.call(now=60, service_up=True)
        ledger = breaker.ledger()
        assert (
            "4 fast failure(s) saved 120 timeout tick(s), "
            "1 probe(s) spent"
        ) in ledger
        assert "outage over after 58 tick(s)" in ledger

    def test_a_quiet_breaker_has_no_episode(self):
        with pytest.raises(Invalid):
            CircuitBreaker(service="x").ledger()
