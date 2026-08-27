"""Single-flight builds: the storm asks four hundred times, the farm builds once.

The minute a core header lands, every developer and every CI
shard asks for the same rebuild, and a naive farm runs the same
ninety-tick action four hundred times in parallel, which is not
load, it is an echo. Single-flight coalesces the storm: the
first request starts the build and becomes the leader, every
duplicate key arriving before completion subscribes to the
leader's result instead of spawning, and completion fans the one
result out to every subscriber. The receipt is the point: ticks
actually spent against ticks the naive farm would have burned,
and the leader's failure is fanned out too, once, honestly,
because four hundred copies of the same red error teach the
same lesson as one at four hundred times the price.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class SingleFlight:
    in_flight: dict[str, list[str]] = field(default_factory=dict)
    results: dict[str, str] = field(default_factory=dict)
    builds_started: int = 0
    subscriptions: int = 0
    ticks_spent: int = 0
    ticks_echo_avoided: int = 0

    def request(
        self, key: str, requester: str, run_ticks: int
    ) -> str:
        if run_ticks <= 0:
            raise Invalid("an action needs positive run ticks")
        if key in self.results:
            return f"{requester}: served from the finished result"
        if key in self.in_flight:
            self.in_flight[key].append(requester)
            self.subscriptions += 1
            self.ticks_echo_avoided += run_ticks
            return (
                f"{requester}: subscribed to the flight already "
                f"underway ({len(self.in_flight[key])} waiting)"
            )
        self.in_flight[key] = []
        self.builds_started += 1
        self.ticks_spent += run_ticks
        return f"{requester}: leader, building"

    def complete(self, key: str, result: str) -> str:
        if key not in self.in_flight:
            raise Invalid(f"{key} has no flight to complete")
        waiters = self.in_flight.pop(key)
        self.results[key] = result
        return (
            f"{result} fanned out to {len(waiters)} "
            f"subscriber(s)"
        )

    def receipt(self) -> str:
        naive = self.ticks_spent + self.ticks_echo_avoided
        return (
            f"{self.builds_started} build(s) for "
            f"{self.builds_started + self.subscriptions} "
            f"request(s): spent {self.ticks_spent} tick(s) "
            f"where the echo pays {naive}"
        )
