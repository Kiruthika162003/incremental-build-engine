"""Cost of delay divided by duration: the queue orders itself.

Platform projects compete for one team, and the argument
about ordering is usually won by whoever spoke last. CD3 ends
it with a ratio: each project carries a cost of delay, what a
week of not having it costs in the currency the farm already
uses, and a duration, and the schedule sorts by cost of delay
divided by duration, which is provably the total-cost-minimal
order for a single queue. The counterintuitive winner is the
short cheap project beating the glamorous long one, the
two-week job with modest weekly savings outranking the
quarter-long flagship, and the report shows the arithmetic
that decides it, because the flagship's sponsor deserves to
see the number that outvoted them. Delay costs nobody can
estimate are not estimated by the tool: a project without a
defensible cost of delay sorts last with that stated, since
inventing the number would just move the argument inside the
spreadsheet.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid


@dataclass(frozen=True)
class Project:
    name: str
    delay_cost_per_week: int | None
    duration_weeks: int

    def __post_init__(self) -> None:
        if self.duration_weeks < 1:
            raise Invalid(
                f"{self.name}: a project with no duration is "
                "a wish"
            )

    def cd3(self) -> float | None:
        if self.delay_cost_per_week is None:
            return None
        return self.delay_cost_per_week / self.duration_weeks


def schedule(projects: list[Project]) -> str:
    if not projects:
        raise Invalid("an empty queue orders itself trivially")
    scored = [
        project
        for project in projects
        if project.cd3() is not None
    ]
    unscored = [
        project
        for project in projects
        if project.cd3() is None
    ]
    scored.sort(key=lambda project: -project.cd3())
    lines = ["the queue, ordered by CD3:"]
    for position, project in enumerate(scored, 1):
        lines.append(
            f"  {position}. {project.name}: "
            f"{project.delay_cost_per_week}/week over "
            f"{project.duration_weeks} week(s) = "
            f"{project.cd3():.0f}"
        )
    for project in unscored:
        lines.append(
            f"  last. {project.name}: no defensible cost of "
            "delay; inventing the number would move the "
            "argument inside the spreadsheet"
        )
    if len(scored) >= 2 and (
        scored[0].duration_weeks < scored[-1].duration_weeks
    ):
        lines.append(
            f"  note: {scored[0].name} outranks "
            f"{scored[-1].name}; the sponsor deserves to see "
            "the number that outvoted them"
        )
    return "\n".join(lines)


def total_delay_cost(ordering: list[Project]) -> int:
    elapsed = 0
    total = 0
    for project in ordering:
        elapsed += project.duration_weeks
        if project.delay_cost_per_week is not None:
            total += project.delay_cost_per_week * elapsed
    return total
