"""The page budget: alert fatigue is a spending problem, not a tuning problem.

A team paged forty times a week stops reading pages, and then
the one page that mattered dies in the pile. The budget caps
pages per team per week, spends one slot per page in severity
order when the router flushes, and overflow does not vanish,
it demotes: everything past the cap lands in a daily digest
with a count, because dropping alerts silently converts a
noisy system into a blind one, which is worse. The ledger is
the tuning tool the cap creates: pages by source across the
window, so the team can see that one flaky monitor spent
two-thirds of the budget, and the demotion line names what the
budget refused, since a cap that cannot show what it cost is
just rate limiting with better branding.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

SEVERITIES = ("critical", "warning", "info")


@dataclass
class PageBudget:
    weekly_cap: int
    queued: list[tuple[str, str, str]] = field(
        default_factory=list
    )
    paged: list[tuple[str, str]] = field(default_factory=list)
    digested: list[tuple[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.weekly_cap < 1:
            raise Invalid(
                "a zero cap is not a budget, it is a blindfold"
            )

    def raise_alert(
        self, source: str, severity: str, message: str
    ) -> None:
        if severity not in SEVERITIES:
            raise Invalid(f"unknown severity {severity}")
        self.queued.append((severity, source, message))

    def flush_week(self) -> str:
        ordered = sorted(
            self.queued,
            key=lambda alert: SEVERITIES.index(alert[0]),
        )
        for _severity, source, message in ordered:
            if len(self.paged) < self.weekly_cap:
                self.paged.append((source, message))
            else:
                self.digested.append((source, message))
        self.queued.clear()
        line = (
            f"{len(self.paged)} paged, {len(self.digested)} "
            "demoted to the daily digest"
        )
        if self.digested:
            line += (
                "; demoted alerts are counted, not dropped, "
                "because a silent drop converts noisy into "
                "blind"
            )
        return line

    def spend_ledger(self) -> str:
        if not self.paged and not self.digested:
            raise Invalid("no alerts this window")
        by_source: dict[str, int] = {}
        for source, _ in self.paged:
            by_source[source] = by_source.get(source, 0) + 1
        lines = [
            f"budget {self.weekly_cap}: "
            f"{len(self.paged)} spent"
        ]
        for source in sorted(
            by_source, key=lambda held: -by_source[held]
        ):
            share = (
                100 * by_source[source] // len(self.paged)
            )
            lines.append(
                f"  {source}: {by_source[source]} page(s) "
                f"({share}% of the budget)"
            )
        top = max(by_source.values(), default=0)
        if top * 3 >= 2 * len(self.paged) and len(by_source) > 1:
            worst = max(by_source, key=lambda held: by_source[held])
            lines.append(
                f"  {worst} spent two-thirds of the budget; "
                "fix the monitor, not the cap"
            )
        return "\n".join(lines)
