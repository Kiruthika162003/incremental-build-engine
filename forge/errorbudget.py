"""The infra error budget: reliability is spent, not hoarded.

A build platform promising 99 percent successful builds has one
percent to spend each window, and both failure modes around
that number are management failures: burning the budget in week
one and freezing all quarter, or finishing the quarter with the
budget untouched, which means the platform moved slower than
its own promise allowed. The ledger burns budget only on infra
faults, worker deaths, cache corruption, queue timeouts, never
on the user's own red tests, because an error budget that
charges users' bugs to the platform teaches the platform to
fear its users. The freeze triggers when the budget is spent,
halting risky platform changes, upgrades, migrations, flag
flips, until the window rolls, and the report says where the
burn went by category, since a budget spent entirely on one
failure class is not bad luck, it is a named project nobody
has staffed yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

INFRA_CATEGORIES = (
    "worker-death",
    "cache-corruption",
    "queue-timeout",
    "network",
)


@dataclass
class ErrorBudget:
    window_builds: int
    promise_percent: float
    burned: list[tuple[str, int]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0 < self.promise_percent < 100:
            raise Invalid(
                "the promise is a percentage strictly between "
                "0 and 100"
            )
        if self.window_builds < 100:
            raise Invalid(
                "a window under 100 builds cannot resolve a "
                "percent promise"
            )

    def total_budget(self) -> int:
        return int(
            self.window_builds * (100 - self.promise_percent) / 100
        )

    def burn(self, category: str, failed_builds: int) -> str:
        if category not in INFRA_CATEGORIES:
            raise Invalid(
                f"{category} is not an infra fault; users' own "
                "red tests never touch this budget, or the "
                "platform learns to fear its users"
            )
        if failed_builds <= 0:
            raise Invalid("a burn needs failures")
        self.burned.append((category, failed_builds))
        remaining = self.remaining()
        if remaining < 0:
            return (
                f"FROZEN: the budget is overspent by "
                f"{-remaining}; risky platform changes halt "
                "until the window rolls"
            )
        return (
            f"{failed_builds} burned on {category}, "
            f"{remaining} of {self.total_budget()} left"
        )

    def remaining(self) -> int:
        return self.total_budget() - sum(
            count for _, count in self.burned
        )

    def window_report(self) -> str:
        spent = sum(count for _, count in self.burned)
        budget = self.total_budget()
        lines = [
            f"window closed: {spent} of {budget} spent"
        ]
        by_category: dict[str, int] = {}
        for category, count in self.burned:
            by_category[category] = (
                by_category.get(category, 0) + count
            )
        for category in sorted(
            by_category, key=lambda c: -by_category[c]
        ):
            share = 100 * by_category[category] // max(spent, 1)
            lines.append(
                f"  {category}: {by_category[category]} "
                f"({share}%)"
            )
        if by_category and max(by_category.values()) > budget // 2:
            worst = max(by_category, key=lambda c: by_category[c])
            lines.append(
                f"  {worst} took over half the budget: not bad "
                "luck, a named project nobody has staffed yet"
            )
        if spent < budget // 4:
            lines.append(
                "  the budget went home unspent: the platform "
                "moved slower than its own promise allowed"
            )
        return "\n".join(lines)
