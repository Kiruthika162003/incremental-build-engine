"""The build cop: broken on main gets quarantined, tracked, and expired.

One target red on main turns every developer's presubmit red for
a failure they did not cause, and the honest fast response is
quarantine: the target is pulled from the blocking set, everyone
else's day resumes, and the breakage becomes an issue with an
owner instead of a shared emergency. The discipline is in the
paperwork the quarantine demands: no entry without an owner and a
tracking issue, every entry carries an expiry, and an expired
entry does not silently extend, it escalates, because a
quarantine list that only grows is a graveyard with optimistic
signage. The exit is verified, not asserted: a quarantined target
must pass twice in a row before rejoining the blocking set, and
the cop's report counts residents by age, since the oldest
resident is the team's real test-health number.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid, Missing

QUARANTINE_TICKS = 50
PASSES_TO_REJOIN = 2


@dataclass
class QuarantineEntry:
    target: str
    owner: str
    issue: str
    entered: int
    expires: int
    consecutive_passes: int = 0


@dataclass
class BuildCop:
    quarantined: dict[str, QuarantineEntry] = field(
        default_factory=dict
    )
    escalations: list[str] = field(default_factory=list)
    rejoined: list[str] = field(default_factory=list)

    def quarantine(
        self, target: str, owner: str, issue: str, now: int
    ) -> str:
        if not owner.strip() or not issue.strip():
            raise Invalid(
                f"{target}: quarantine without an owner and an issue "
                f"is a graveyard with optimistic signage"
            )
        if target in self.quarantined:
            raise Invalid(f"{target} is already quarantined")
        self.quarantined[target] = QuarantineEntry(
            target=target,
            owner=owner,
            issue=issue,
            entered=now,
            expires=now + QUARANTINE_TICKS,
        )
        return (
            f"{target} quarantined until {now + QUARANTINE_TICKS}; "
            f"{owner} owns {issue}; everyone else's day resumes"
        )

    def blocking_set(self, all_targets: list[str]) -> list[str]:
        return sorted(
            target
            for target in all_targets
            if target not in self.quarantined
        )

    def record_run(self, target: str, passed: bool) -> str:
        entry = self.quarantined.get(target)
        if entry is None:
            raise Missing(f"{target} is not quarantined")
        if not passed:
            entry.consecutive_passes = 0
            return f"{target} still failing; the clock keeps running"
        entry.consecutive_passes += 1
        if entry.consecutive_passes >= PASSES_TO_REJOIN:
            del self.quarantined[target]
            self.rejoined.append(target)
            return f"{target} passed twice and rejoins the blocking set"
        return (
            f"{target} passed once; one more before it rejoins"
        )

    def patrol(self, now: int) -> list[str]:
        flagged = []
        for entry in sorted(
            self.quarantined.values(), key=lambda held: held.target
        ):
            if now >= entry.expires and entry.target not in [
                line.split(":")[0] for line in self.escalations
            ]:
                line = (
                    f"{entry.target}: expired in quarantine; "
                    f"escalating past {entry.owner} on {entry.issue}"
                )
                self.escalations.append(line)
                flagged.append(line)
        return flagged

    def report(self, now: int) -> str:
        if not self.quarantined:
            return (
                f"quarantine empty; {len(self.rejoined)} rejoined to "
                f"date"
            )
        by_age = sorted(
            self.quarantined.values(),
            key=lambda entry: entry.entered,
        )
        lines = [
            f"{entry.target}: {now - entry.entered} ticks inside, "
            f"{entry.owner} on {entry.issue}"
            for entry in by_age
        ]
        oldest = by_age[0]
        lines.append(
            f"the oldest resident is {oldest.target} at "
            f"{now - oldest.entered} ticks; that is the real "
            f"test-health number"
        )
        return "\n".join(lines)
