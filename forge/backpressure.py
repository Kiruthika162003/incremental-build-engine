"""Backpressure: the honest queue says no at the door, not in the hallway.

When the artifact store slows down, an unbounded upload queue
absorbs the slowness silently, growing until memory or
patience runs out, and the failure lands hours later on
whoever is standing nearest. Bounded queues propagate the
truth upstream instead: when the queue is full, admission
refuses immediately, the producer learns the system's real
capacity while there is still time to react, and the refusal
carries the queue's depth and drain rate so the caller can
distinguish a blip from a collapse. The choice being priced is
latency of bad news, buffered slowness arrives late and
everywhere, backpressure arrives instantly and precisely, and
the ledger counts what the bound refused next to what the
buffer would have swallowed, because the swallowed number is
the debt an unbounded queue quietly signs everyone up for.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid


@dataclass
class BoundedQueue:
    capacity: int
    drain_per_tick: int
    held: int = 0
    refused: int = 0
    admitted: int = 0
    would_have_buffered: int = 0

    def __post_init__(self) -> None:
        if self.capacity < 1 or self.drain_per_tick < 1:
            raise Invalid(
                "a queue needs capacity and a drain, or it is "
                "a wall or a pipe"
            )

    def offer(self, items: int) -> str:
        if items < 1:
            raise Invalid("offer something")
        space = self.capacity - self.held
        taken = min(items, space)
        turned_away = items - taken
        self.held += taken
        self.admitted += taken
        if turned_away:
            self.refused += turned_away
            self.would_have_buffered += turned_away
            eta = self.held // self.drain_per_tick
            return (
                f"{taken} admitted, {turned_away} refused at "
                f"the door: depth {self.held}/{self.capacity}, "
                f"draining {self.drain_per_tick}/tick, "
                f"roughly {eta} tick(s) to clear; decide now "
                "whether this is a blip or a collapse"
            )
        return f"{taken} admitted quietly"

    def drain_tick(self) -> None:
        self.held = max(0, self.held - self.drain_per_tick)

    def ledger(self) -> str:
        return (
            f"{self.admitted} admitted, {self.refused} refused "
            f"instantly; an unbounded queue would have "
            f"swallowed {self.would_have_buffered} and served "
            "the bad news hours later to whoever stood nearest"
        )
