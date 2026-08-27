"""Interruption: ctrl-C is a request, and the build honours it cleanly.

Killing a build mid-flight leaves half-written outputs and orphan
processes unless someone planned for the signal. The controller
turns interruption into a protocol: a cancel request stops new
actions from starting immediately, running actions are given a
grace window to finish because a compile two ticks from done is
cheaper finished than redone, and whatever outlives the grace is
killed with its partial outputs discarded rather than promoted.
The receipt is what makes the next build fast: everything that
completed before the cancel is cache-warm, everything killed is
honestly absent, and the resume line predicts the next build's
work as exactly the killed plus the never-started, a promise the
tests verify because a resume estimate that lies teaches people
to fear ctrl-C, and fearing ctrl-C is how zombie builds happen.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

GRACE_TICKS = 5


@dataclass
class InFlight:
    action: str
    finishes_at: int


@dataclass
class CancelController:
    total_actions: list[str]
    completed: list[str] = field(default_factory=list)
    running: list[InFlight] = field(default_factory=list)
    killed: list[str] = field(default_factory=list)
    cancel_requested_at: int | None = None

    def start(self, action: str, now: int, takes: int) -> str:
        if action not in self.total_actions:
            raise Invalid(f"{action} is not part of this build")
        if self.cancel_requested_at is not None:
            return "refused: the build is cancelling"
        self.running.append(
            InFlight(action=action, finishes_at=now + takes)
        )
        return "started"

    def tick(self, now: int) -> None:
        still = []
        for flight in self.running:
            if flight.finishes_at <= now:
                self.completed.append(flight.action)
            else:
                still.append(flight)
        self.running = still
        if (
            self.cancel_requested_at is not None
            and now >= self.cancel_requested_at + GRACE_TICKS
        ):
            for flight in self.running:
                self.killed.append(flight.action)
            self.running = []

    def cancel(self, now: int) -> str:
        if self.cancel_requested_at is not None:
            raise Invalid("the build is already cancelling")
        self.cancel_requested_at = now
        return (
            f"cancelling: nothing new starts, {len(self.running)} "
            f"in flight get {GRACE_TICKS} ticks of grace"
        )

    def receipt(self) -> str:
        never_started = [
            action
            for action in self.total_actions
            if action not in self.completed
            and action not in self.killed
        ]
        return (
            f"{len(self.completed)} completed and cache-warm, "
            f"{len(self.killed)} killed and honestly absent, "
            f"{len(never_started)} never started; the next build "
            f"owes {len(self.killed) + len(never_started)} actions"
        )

    def next_build_owes(self) -> list[str]:
        return sorted(
            action
            for action in self.total_actions
            if action not in self.completed
        )
