"""Failure-first ordering: red arrives sooner when history picks the order.

A suite that fails in minute nine after a nine-minute run wasted
nothing; the same failure in minute one of the same run returns
eight minutes to the developer, and the only difference is
order. The scheduler ranks tests by their historical failure
rate with a recency thumb on the scale, runs the likeliest
failures first, and meters what the ordering actually buys:
time-to-first-red under history order against alphabetical
order, which is the number that justifies keeping the history.
Fresh tests with no record run early too, because an unknown
test is a risk, not a pass, and the decay keeps the ranking
honest: a test that failed all spring and passed all summer
drifts down instead of haunting the front of the line forever.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

HISTORY_WINDOW = 10
FRESH_RISK = 0.5


@dataclass
class FailureHistory:
    outcomes: dict[str, list[bool]] = field(default_factory=dict)

    def record(self, test: str, passed: bool) -> None:
        held = self.outcomes.setdefault(test, [])
        held.append(passed)
        if len(held) > HISTORY_WINDOW:
            held.pop(0)

    def failure_score(self, test: str) -> float:
        held = self.outcomes.get(test)
        if not held:
            return FRESH_RISK
        weighted = 0.0
        weight_total = 0.0
        for age, passed in enumerate(reversed(held)):
            weight = 1.0 / (age + 1)
            weight_total += weight
            if not passed:
                weighted += weight
        return weighted / weight_total


@dataclass
class FailFirstScheduler:
    history: FailureHistory
    costs: dict[str, int]

    def order(self) -> list[str]:
        if not self.costs:
            raise Invalid("no tests to order")
        return sorted(
            self.costs,
            key=lambda test: (
                -self.history.failure_score(test),
                test,
            ),
        )

    def time_to_first_red(
        self, failing: set[str], ordering: list[str]
    ) -> int | None:
        elapsed = 0
        for test in ordering:
            elapsed += self.costs[test]
            if test in failing:
                return elapsed
        return None

    def savings_report(self, failing: set[str]) -> str:
        smart = self.time_to_first_red(failing, self.order())
        naive = self.time_to_first_red(
            failing, sorted(self.costs)
        )
        if smart is None or naive is None:
            return (
                "a green run pays the full suite either way; "
                "ordering buys nothing today"
            )
        saved = naive - smart
        return (
            f"first red at {smart} ticks with history order, "
            f"{naive} alphabetical: {saved} tick(s) returned to "
            "the developer"
        )
