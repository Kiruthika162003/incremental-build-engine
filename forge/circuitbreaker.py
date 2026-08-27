"""The circuit breaker: fail fast while the registry is down, probe politely.

An external registry that starts timing out does not need
four hundred builds to confirm it, and every build that waits
the full timeout to learn what the last one learned donates
its developer's time to an outage. The breaker counts recent
failures against a trip threshold: closed, it passes calls
through; open, it refuses instantly with the outage named,
converting timeout waits into fast failures; and after a
cool-down it goes half-open, spending one probe call on the
question everyone wants answered, is it back. A probe success
closes the breaker, a probe failure reopens it with the clock
reset, and the ledger prices the whole episode in the currency
that justifies the pattern: timeout ticks not waited, probe
calls spent, and the one number nobody tracks without a
breaker, how long the outage actually lasted from first trip
to closing probe.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

TRIP_AFTER = 3
COOLDOWN_TICKS = 50
TIMEOUT_TICKS = 30


@dataclass
class CircuitBreaker:
    service: str
    state: str = "closed"
    recent_failures: int = 0
    opened_at: int | None = None
    first_trip_at: int | None = None
    fast_fails: int = 0
    probes_spent: int = 0
    log: list[str] = field(default_factory=list)

    def call(self, now: int, service_up: bool) -> str:
        if self.state == "open":
            if now - self.opened_at >= COOLDOWN_TICKS:
                self.state = "half-open"
            else:
                self.fast_fails += 1
                return (
                    f"{self.service} is down (breaker open): "
                    "refused instantly instead of waiting "
                    f"{TIMEOUT_TICKS} ticks to learn what the "
                    "last build learned"
                )
        if self.state == "half-open":
            self.probes_spent += 1
            if service_up:
                self.state = "closed"
                self.recent_failures = 0
                outage = now - self.first_trip_at
                self.log.append(
                    f"outage over after {outage} tick(s)"
                )
                self.first_trip_at = None
                return (
                    f"probe succeeded; {self.service} is back "
                    "and the breaker closes"
                )
            self.state = "open"
            self.opened_at = now
            return (
                "probe failed; the breaker reopens and the "
                "clock resets"
            )
        if service_up:
            self.recent_failures = 0
            return f"{self.service} answered"
        self.recent_failures += 1
        if self.recent_failures >= TRIP_AFTER:
            self.state = "open"
            self.opened_at = now
            if self.first_trip_at is None:
                self.first_trip_at = now
            return (
                f"{self.service} tripped the breaker after "
                f"{TRIP_AFTER} failure(s); further calls fail "
                "fast"
            )
        return (
            f"{self.service} timed out "
            f"({self.recent_failures}/{TRIP_AFTER})"
        )

    def ledger(self) -> str:
        if self.fast_fails == 0 and self.probes_spent == 0:
            raise Invalid("no episode to price")
        saved = self.fast_fails * TIMEOUT_TICKS
        line = (
            f"{self.fast_fails} fast failure(s) saved {saved} "
            f"timeout tick(s), {self.probes_spent} probe(s) "
            "spent"
        )
        if self.log:
            line += f"; {self.log[-1]}"
        return line
