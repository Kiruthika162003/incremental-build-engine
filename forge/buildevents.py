"""The event stream: everything the build did, in the order it did it.

Dashboards, IDEs, and CI annotators all want to watch a build, and
each one screen-scraping the log invents its own parser and its
own bugs. The stream is the single contract: typed events with a
monotonic sequence number, emitted at start, at every action state
change, and at finish, with the invariant checker enforcing the
grammar an observer may rely on: one started and one finished, no
action events outside that bracket, every action that starts also
ends, and sequence numbers dense from one. Consumers subscribe by
event kind, a late subscriber can replay from any sequence number,
and the checker exists because a stream whose grammar drifts turns
every consumer into a defensive parser again, which is the disease
the stream was meant to cure.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid, Stale


@dataclass(frozen=True)
class Event:
    sequence: int
    kind: str
    target: str = ""
    detail: str = ""

    def line(self) -> str:
        body = f" {self.target}" if self.target else ""
        tail = f" ({self.detail})" if self.detail else ""
        return f"[{self.sequence}] {self.kind}{body}{tail}"


KINDS = (
    "started",
    "action-queued",
    "action-running",
    "action-done",
    "action-cached",
    "finished",
)


@dataclass
class EventStream:
    events: list[Event] = field(default_factory=list)
    next_sequence: int = 1

    def emit(self, kind: str, target: str = "", detail: str = "") -> Event:
        if kind not in KINDS:
            raise Invalid(
                f"unknown event kind {kind!r}; the grammar has {KINDS}"
            )
        event = Event(
            sequence=self.next_sequence,
            kind=kind,
            target=target,
            detail=detail,
        )
        self.events.append(event)
        self.next_sequence += 1
        return event

    def replay_from(self, sequence: int) -> list[Event]:
        if sequence > self.next_sequence:
            raise Stale(
                f"sequence {sequence} is beyond the stream's "
                f"{self.next_sequence - 1}"
            )
        return [
            event for event in self.events if event.sequence >= sequence
        ]

    def of_kind(self, kind: str) -> list[Event]:
        return [event for event in self.events if event.kind == kind]

    def check_grammar(self) -> list[str]:
        complaints = []
        sequences = [event.sequence for event in self.events]
        if sequences != list(range(1, len(sequences) + 1)):
            complaints.append("sequence numbers are not dense from one")
        starts = self.of_kind("started")
        ends = self.of_kind("finished")
        if len(starts) != 1:
            complaints.append(f"{len(starts)} started events; wanted 1")
        if len(ends) != 1:
            complaints.append(f"{len(ends)} finished events; wanted 1")
        if starts and ends:
            bracket = range(
                starts[0].sequence + 1, ends[0].sequence
            )
            for event in self.events:
                if event.kind in ("started", "finished"):
                    continue
                if event.sequence not in bracket:
                    complaints.append(
                        f"{event.line()} falls outside the bracket"
                    )
        running = {
            event.target for event in self.of_kind("action-running")
        }
        finished_targets = {
            event.target for event in self.of_kind("action-done")
        }
        for target in sorted(running - finished_targets):
            complaints.append(f"{target} started but never ended")
        return complaints
