"""Event debouncing: the editor saves in bursts, the build starts once.

A format-on-save plus a linter plus the editor's own write can
touch one file four times in half a second, and a watcher that
starts a build per event runs three builds that are stale before
they finish. The debouncer holds each burst open while events
keep arriving inside the quiet window and releases one batch when
the window finally passes in silence, so the build starts once
with the final state of every file the burst touched. The ceiling
is what keeps a chatty tool honest: a burst that never goes quiet
is force-released at the deadline rather than deferred forever,
because a build system waiting politely for a log writer to stop
writing waits until retirement. The ledger counts events in,
batches out, and builds saved, since the debouncer's salary is
the difference between the first two numbers.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

QUIET_WINDOW = 3
FORCE_CEILING = 12


@dataclass
class Debouncer:
    pending: dict[str, int] = field(default_factory=dict)
    burst_started_at: int | None = None
    last_event_at: int | None = None
    events_in: int = 0
    batches_out: int = 0
    force_releases: int = 0

    def event(self, path: str, now: int) -> None:
        if self.burst_started_at is None:
            self.burst_started_at = now
        self.last_event_at = now
        self.pending[path] = self.pending.get(path, 0) + 1
        self.events_in += 1

    def poll(self, now: int) -> list[str] | None:
        if self.burst_started_at is None:
            return None
        quiet = now - self.last_event_at >= QUIET_WINDOW
        overdue = now - self.burst_started_at >= FORCE_CEILING
        if not quiet and not overdue:
            return None
        if overdue and not quiet:
            self.force_releases += 1
        batch = sorted(self.pending)
        self.pending.clear()
        self.burst_started_at = None
        self.last_event_at = None
        self.batches_out += 1
        return batch

    def salary(self) -> str:
        if self.events_in == 0:
            raise Invalid("no events yet; the debouncer is unemployed")
        saved = self.events_in - self.batches_out
        return (
            f"{self.events_in} events became {self.batches_out} "
            f"batches; {saved} builds never started "
            f"({self.force_releases} force releases)"
        )
