"""Fair-share scheduling: the farm remembers who has been eating.

A farm shared by teams without accounting is a farm owned by the
team with the most cron jobs. Fair share fixes it with memory
instead of quotas: every team's usage accumulates, decays by
half each accounting period so last month's feast fades, and the
next free slot goes to the team furthest below its entitled
share. The arithmetic has two properties worth testing rather
than asserting: a team that stops submitting stops being
charged, and a team that has been starved rises monotonically
toward the front, so starvation is impossible as long as decay
runs. The report shows each team's decayed usage against its
entitlement, because "you are over your share" lands differently
when the number is printed next to the neighbor's.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class FairShare:
    entitlements: dict[str, float]
    usage: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.entitlements:
            raise Invalid("a farm with no teams needs no scheduler")
        total = sum(self.entitlements.values())
        if abs(total - 1.0) > 1e-9:
            raise Invalid(
                f"entitlements must sum to 1, got {total}"
            )
        for team in self.entitlements:
            self.usage.setdefault(team, 0.0)

    def charge(self, team: str, ticks: int) -> None:
        if team not in self.entitlements:
            raise Invalid(f"{team} is not on this farm")
        if ticks <= 0:
            raise Invalid("a charge must be positive")
        self.usage[team] += ticks

    def decay(self) -> None:
        for team in self.usage:
            self.usage[team] /= 2

    def _pressure(self, team: str) -> float:
        total_usage = sum(self.usage.values())
        if total_usage == 0:
            return -self.entitlements[team]
        observed = self.usage[team] / total_usage
        return observed - self.entitlements[team]

    def next_slot(self) -> str:
        return min(
            sorted(self.entitlements),
            key=lambda team: (self._pressure(team), team),
        )

    def report(self) -> str:
        total_usage = sum(self.usage.values())
        lines = []
        for team in sorted(self.entitlements):
            entitled = self.entitlements[team]
            observed = (
                self.usage[team] / total_usage
                if total_usage
                else 0.0
            )
            state = (
                "over" if observed > entitled else "under"
            )
            lines.append(
                f"{team}: using {observed:.0%} of an entitled "
                f"{entitled:.0%} ({state})"
            )
        lines.append(f"next slot: {self.next_slot()}")
        return "\n".join(lines)
