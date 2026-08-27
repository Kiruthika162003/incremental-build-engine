"""Autoscaling the farm: scale up on the queue, down on the calendar.

A build farm sized for the afternoon burns money all night, and
one sized for the night melts every afternoon, so the fleet has
to move, and how it moves matters more than where it sits. The
policy is asymmetric on purpose: scale up immediately when queue
depth crosses the threshold, because developers are waiting and
wait is the expensive resource, but scale down only after the
queue has been quiet for a full cool period, because workers that
flap pay boot cost at both edges and a queue oscillating around
the threshold would otherwise thrash the fleet. The ledger prices
the policy honestly in both currencies, idle worker ticks and
queued build ticks, since either number alone justifies any
policy and only the pair convicts one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class AutoScaler:
    min_workers: int
    max_workers: int
    depth_per_worker: int
    cool_ticks: int
    workers: int = 0
    quiet_streak: int = 0
    idle_ticks: int = 0
    queued_ticks: int = 0
    scale_ups: int = 0
    scale_downs: int = 0
    events: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.min_workers < 1 or self.max_workers < self.min_workers:
            raise Invalid(
                "the fleet needs 1 <= min <= max workers"
            )
        if self.depth_per_worker < 1 or self.cool_ticks < 1:
            raise Invalid(
                "depth per worker and cool ticks must be positive"
            )
        if not self.workers:
            self.workers = self.min_workers

    def tick(self, queue_depth: int) -> int:
        if queue_depth < 0:
            raise Invalid("queue depth cannot be negative")
        wanted = min(
            self.max_workers,
            max(
                self.min_workers,
                -(-queue_depth // self.depth_per_worker),
            ),
        )
        if wanted > self.workers:
            self.events.append(
                f"scale up {self.workers} -> {wanted} "
                f"(depth {queue_depth})"
            )
            self.workers = wanted
            self.scale_ups += 1
            self.quiet_streak = 0
        elif wanted < self.workers:
            self.quiet_streak += 1
            if self.quiet_streak >= self.cool_ticks:
                self.events.append(
                    f"scale down {self.workers} -> {wanted} "
                    f"after {self.quiet_streak} quiet tick(s)"
                )
                self.workers = wanted
                self.scale_downs += 1
                self.quiet_streak = 0
        else:
            self.quiet_streak = 0
        busy = min(queue_depth, self.workers)
        self.idle_ticks += self.workers - busy
        self.queued_ticks += max(0, queue_depth - self.workers)
        return self.workers

    def bill(self) -> str:
        return (
            f"{self.scale_ups} scale-up(s), "
            f"{self.scale_downs} scale-down(s), "
            f"{self.idle_ticks} idle worker tick(s), "
            f"{self.queued_ticks} queued build tick(s)"
        )
