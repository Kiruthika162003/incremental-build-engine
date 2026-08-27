"""The on-call handover: nothing in flight goes unmentioned.

The worst hour of an on-call week is the first one, inherited
blind, and the handover note exists to make it boring. The
builder tracks what the outgoing shift holds, open incidents,
armed breakers, unexpired break-glass grants, watches on
erratic disks, and refuses to generate the note while any
in-flight item is unmentioned, because the sentence "quiet
week" with an open incident behind it is not a handover, it
is a trap with a greeting. Every mentioned item carries its
next expected event, the probe due at sixty, the grant
expiring at midnight, so the incoming shift inherits a
calendar instead of a mood, and the note closes with the
outgoing engineer's name, since accountability is the part of
the format that keeps the format honest.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class Handover:
    outgoing: str
    in_flight: dict[str, str] = field(default_factory=dict)
    mentioned: dict[str, str] = field(default_factory=dict)

    def track(self, item: str, next_event: str) -> None:
        if not next_event.strip():
            raise Invalid(
                f"{item}: an in-flight item without its next "
                "expected event is a mood, not a calendar"
            )
        self.in_flight[item] = next_event

    def resolve(self, item: str) -> None:
        if item not in self.in_flight:
            raise Invalid(f"{item} was not in flight")
        del self.in_flight[item]
        self.mentioned.pop(item, None)

    def mention(self, item: str, note: str) -> None:
        if item not in self.in_flight:
            raise Invalid(
                f"{item} is not in flight; notes about "
                "finished business belong in the chronicle"
            )
        self.mentioned[item] = note

    def note(self) -> str:
        unmentioned = sorted(
            set(self.in_flight) - set(self.mentioned)
        )
        if unmentioned:
            raise Invalid(
                f"REFUSED: {', '.join(unmentioned)} in flight "
                "and unmentioned; a quiet-week note with an "
                "open incident behind it is a trap with a "
                "greeting"
            )
        if not self.in_flight:
            return (
                f"genuinely quiet; nothing in flight. "
                f"({self.outgoing})"
            )
        lines = [
            f"{len(self.in_flight)} item(s) in flight:"
        ]
        for item in sorted(self.in_flight):
            lines.append(
                f"  {item}: {self.mentioned[item]}; next: "
                f"{self.in_flight[item]}"
            )
        lines.append(
            f"you inherit a calendar, not a mood. "
            f"({self.outgoing})"
        )
        return "\n".join(lines)
