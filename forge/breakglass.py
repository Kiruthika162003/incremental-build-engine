"""Break-glass access: the emergency door works, expires, and testifies.

Every locked-down farm needs an emergency door, and the two
ways to build it wrong are famous: no door, so the outage
waits for a change-review meeting, or a door that shuts
quietly behind whoever used it, so emergency access becomes
everyday access one convenience at a time. The break-glass
grant opens on a named incident with a named human, carries an
expiry chosen at open time, and every privileged action taken
through it lands in the grant's own testimony. Expiry is
enforced at use, an action after the deadline is refused with
the timestamp, and closing the incident before expiry is
rewarded in the record, because the metric that keeps the door
honest is not how often it opens but how long it stays open,
and the quarterly review reads the testimony, not the vibes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class BreakGlass:
    incident: str
    human: str
    opened_at: int
    expires_at: int
    actions: list[str] = field(default_factory=list)
    closed_at: int | None = None

    def __post_init__(self) -> None:
        if not self.incident.strip() or not self.human.strip():
            raise Invalid(
                "the glass breaks for a named incident and a "
                "named human, or it does not break"
            )
        if self.expires_at <= self.opened_at:
            raise Invalid("the grant must expire after it opens")

    def act(self, what: str, now: int) -> str:
        if self.closed_at is not None:
            raise Invalid(
                f"the grant closed at {self.closed_at}; "
                "reopening is a new incident, not a habit"
            )
        if now >= self.expires_at:
            raise Invalid(
                f"the grant expired at {self.expires_at} and "
                f"it is {now}; the emergency door does not "
                "stay propped"
            )
        entry = f"[{now}] {self.human}: {what}"
        self.actions.append(entry)
        return entry

    def close(self, now: int) -> str:
        if self.closed_at is not None:
            raise Invalid("already closed")
        self.closed_at = now
        early = self.expires_at - now
        if early > 0:
            return (
                f"closed {early} tick(s) early; the record "
                "rewards doors that shut before they must"
            )
        return "closed at expiry"

    def testimony(self) -> str:
        state = (
            f"closed at {self.closed_at}"
            if self.closed_at is not None
            else f"OPEN until {self.expires_at}"
        )
        lines = [
            f"{self.incident} ({self.human}), opened "
            f"{self.opened_at}, {state}, "
            f"{len(self.actions)} privileged action(s)"
        ]
        lines.extend(f"  {entry}" for entry in self.actions)
        lines.append(
            "the metric that keeps the door honest is how "
            "long it stays open, not how often it opens"
        )
        return "\n".join(lines)
