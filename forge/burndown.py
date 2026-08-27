"""The honest burndown: scope added mid-sprint gets its own line.

A burndown that only plots remaining work hides the most
common failure inside its slope: the team burned forty points
and the chart barely moved because thirty new points walked
in the side door, and the retrospective blames velocity when
the story is scope. The honest chart keeps two series, work
completed and scope added, day by day, so the flat line
explains itself, and the closing summary attributes the gap
between plan and outcome to its true parts: the team burned
what it promised, the sprint absorbed what it did not, and
the difference between those sentences decides whether the
fix is estimation or door control. The refusal is small and
firm: scope additions cannot be logged as negative burn,
because a chart that nets the two is a chart built to end
the conversation the numbers should start.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class Burndown:
    planned_points: int
    burned: list[int] = field(default_factory=list)
    added: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.planned_points <= 0:
            raise Invalid("a sprint needs planned points")

    def record_day(
        self, burned: int, scope_added: int = 0
    ) -> None:
        if burned < 0 or scope_added < 0:
            raise Invalid(
                "scope additions are logged as additions, "
                "never as negative burn; netting the two "
                "builds a chart that ends the conversation "
                "the numbers should start"
            )
        self.burned.append(burned)
        self.added.append(scope_added)

    def remaining(self) -> int:
        return (
            self.planned_points
            + sum(self.added)
            - sum(self.burned)
        )

    def closing_summary(self) -> str:
        if not self.burned:
            raise Invalid("no days recorded")
        total_burn = sum(self.burned)
        total_added = sum(self.added)
        left = self.remaining()
        lines = [
            f"planned {self.planned_points}, burned "
            f"{total_burn}, absorbed {total_added}, "
            f"{left} remaining"
        ]
        if total_burn >= self.planned_points and left > 0:
            lines.append(
                "  the team burned what it promised and the "
                "sprint absorbed what it did not; the fix is "
                "door control, not estimation"
            )
        elif total_burn < self.planned_points and (
            total_added == 0
        ):
            lines.append(
                "  the scope held and the burn fell short; "
                "the fix is estimation, not door control"
            )
        return "\n".join(lines)
