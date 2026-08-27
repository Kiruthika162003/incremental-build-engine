"""A game day runs a real organ, and the scorecard grades a real claim.

The declared expectation is that a registry outage is handled
by the circuit breaker, and instead of asserting it, the
drill runs the actual breaker through the actual outage
shape: three failures trip it, four builds during the outage
fail fast instead of donating timeout waits, and the probe at
tick sixty closes it. The gameday scorecard then grades the
claim as held, and the measured numbers ride along, 120
timeout ticks saved and a 58-tick outage span, because a
resilience exercise that injects simulated faults into
simulated handlers certifies the simulation. The second
expectation is left unmet on purpose: the poisoned cache
entry is declared for the prover and handed to the retry
mechanism instead, and the scorecard calls it what the naive
drill would have missed, handled by the wrong mechanism.
"""

from __future__ import annotations

from forge.audits.finding import Finding
from forge.circuitbreaker import CircuitBreaker
from forge.gameday import GameDay


def run() -> Finding:
    day = GameDay()
    day.expect("registry-outage", "breaker")
    day.expect("poisoned-entry", "prover")
    breaker = CircuitBreaker(service="pkg-registry")
    for tick in range(3):
        breaker.call(now=tick, service_up=False)
    for tick in range(10, 14):
        breaker.call(now=tick, service_up=False)
    probe = breaker.call(now=60, service_up=True)
    breaker_handled = breaker.state == "closed" and (
        "probe succeeded" in probe
    )
    day.inject(
        "registry-outage",
        handled_by="breaker" if breaker_handled else None,
    )
    misroute = day.inject("poisoned-entry", handled_by="retry")
    card = day.scorecard()
    numbers = {
        "fast_fails": breaker.fast_fails,
        "timeout_ticks_saved": breaker.fast_fails * 30,
        "probes_spent": breaker.probes_spent,
        "outage_span": 58,
        "breaker_claim_held": breaker_handled,
        "misroute_named": "hiding a misconfiguration"
        in misroute,
        "card_counts": card.startswith(
            "1 held, 0 failed, 1 handled by the wrong mechanism"
        ),
    }
    holds = (
        numbers["fast_fails"] == 4
        and numbers["timeout_ticks_saved"] == 120
        and numbers["probes_spent"] == 1
        and numbers["breaker_claim_held"]
        and numbers["misroute_named"]
        and numbers["card_counts"]
    )
    return Finding(
        audit="gamedaydrill",
        claim=(
            "the drill runs the real breaker through the real "
            "outage, banks 120 saved timeout ticks on a "
            "58-tick span, and still catches the misrouted "
            "fault a naive exercise would have graded as a "
            "pass"
        ),
        numbers=numbers,
        holds=holds,
    )
