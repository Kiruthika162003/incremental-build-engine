"""Shadow lint: the new rule watches quietly before it gets a hammer.

Turning on a lint rule and its enforcement in the same commit
is how a Tuesday becomes four hundred broken builds, so new
rules serve a shadow term: they run on every build, report
what they would have flagged, and block nothing. The shadow
era measures the two numbers promotion actually depends on:
volume, how many existing violations the codebase carries,
and velocity, whether new violations are still being written,
because a rule with high volume and zero velocity wants a
one-time cleanup plus a ratchet, while a rule with live
velocity wants education before enforcement, and neither is
learned by breaking the build. Promotion is a gate, not a
date: stable volume, near-zero velocity for the probation
window, and the promotion note records both numbers so the
next rule's shadow term has a precedent instead of a debate.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

PROBATION_WEEKS = 3


@dataclass
class ShadowRule:
    name: str
    weekly_counts: list[int] = field(default_factory=list)
    promoted: bool = False

    def observe_week(self, violations: int) -> None:
        if self.promoted:
            raise Invalid(
                f"{self.name} is enforced; shadows are for "
                "the unproven"
            )
        if violations < 0:
            raise Invalid("violations cannot be negative")
        self.weekly_counts.append(violations)

    def velocity(self) -> int:
        if len(self.weekly_counts) < 2:
            raise Invalid("velocity needs two weeks")
        return self.weekly_counts[-1] - self.weekly_counts[-2]

    def promotion_gate(self) -> str:
        if len(self.weekly_counts) < PROBATION_WEEKS:
            return (
                f"{self.name}: {len(self.weekly_counts)} of "
                f"{PROBATION_WEEKS} probation week(s) served"
            )
        recent = self.weekly_counts[-PROBATION_WEEKS:]
        spread = max(recent) - min(recent)
        if spread > max(recent) // 10 + 1:
            return (
                f"{self.name}: volume still moving (spread "
                f"{spread} across {recent}); a rule with live "
                "velocity wants education before enforcement"
            )
        self.promoted = True
        return (
            f"{self.name} PROMOTED: volume stable at "
            f"{recent[-1]}, velocity ~0; cleanup plus ratchet "
            "for the stock, enforcement for the flow, and "
            "these numbers are the next rule's precedent"
        )
