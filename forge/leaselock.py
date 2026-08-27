"""Lease leadership: one coordinator at a time, enforced by fencing, not faith.

Two coordinators both believing they lead is the distributed
system's oldest injury, and it never announces itself; it just
writes twice. The lease makes leadership a temporary fact with
an expiry: a coordinator acquires the lease with a fencing
token that increments monotonically, renews before expiry, and
loses leadership by clock, not by courtesy, when the renewal
is late. The fencing token is the half teams skip: every write
carries the writer's token, and the store refuses any write
bearing a token older than the newest it has seen, so the old
leader who wakes from a garbage-collection pause and still
believes cannot hurt anything, its writes bounce off the fence
with the token gap named. Split brain is thereby converted
from a corruption event into a log line, which is the entire
budget of the design.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

LEASE_TICKS = 30


@dataclass
class LeaseStore:
    holder: str | None = None
    token: int = 0
    expires_at: int = 0
    highest_write_token: int = 0
    fenced_writes: list[str] = field(default_factory=list)
    log: list[str] = field(default_factory=list)

    def acquire(self, candidate: str, now: int) -> str:
        if self.holder is not None and now < self.expires_at:
            raise Invalid(
                f"{self.holder} holds the lease until "
                f"{self.expires_at}; {candidate} waits"
            )
        self.holder = candidate
        self.token += 1
        self.expires_at = now + LEASE_TICKS
        self.log.append(
            f"{candidate} leads with token {self.token} "
            f"until {self.expires_at}"
        )
        return self.log[-1]

    def renew(self, holder: str, now: int) -> str:
        if holder != self.holder:
            raise Invalid(
                f"{holder} cannot renew a lease it does not hold"
            )
        if now >= self.expires_at:
            raise Invalid(
                f"{holder} renewed late at {now}; leadership "
                "was lost by clock, not courtesy, at "
                f"{self.expires_at}"
            )
        self.expires_at = now + LEASE_TICKS
        return f"{holder} renewed until {self.expires_at}"

    def write(self, writer: str, token: int, what: str) -> str:
        if token < self.highest_write_token:
            refusal = (
                f"{writer} writes with token {token} against a "
                f"fence at {self.highest_write_token}: the old "
                "leader woke up still believing, and its write "
                "bounces off the fence"
            )
            self.fenced_writes.append(refusal)
            raise Invalid(refusal)
        self.highest_write_token = token
        return f"{what} written under token {token}"

    def incident_summary(self) -> str:
        if not self.fenced_writes:
            return (
                "no fenced writes; either no split brain, or "
                "nobody wrote during one"
            )
        return (
            f"{len(self.fenced_writes)} split-brain write(s) "
            "converted from corruption into log lines, which "
            "is the entire budget of the design"
        )
