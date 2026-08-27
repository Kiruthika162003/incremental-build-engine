"""The runaway build: killed at the cap, with the biggest action named.

Per-action deadlines catch the hung compile; they miss the
build that is perfectly alive and quietly infinite, ten
thousand legitimate actions nobody expected, a glob that
matched a vendored kernel, codegen feeding itself. The build
cap is the outer wall: a tick ceiling for the whole build,
generous enough that no honest build ever meets it, and when
it is crossed the kill arrives with a report instead of a
shrug, total spent, action count, and the biggest single
spender named, because the difference between "your build
was killed" and "your build was killed after codegen-loop
spent 40 percent of the budget" is the difference between a
ticket and a fix. The cap refuses to be set stingy: a ceiling
under the observed honest maximum is rejected, since a wall
that honest builds hit is not a safety net, it is a lottery.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class BuildCap:
    ceiling_ticks: int
    honest_maximum: int
    spent: dict[str, int] = field(default_factory=dict)
    killed: bool = False

    def __post_init__(self) -> None:
        if self.ceiling_ticks <= self.honest_maximum:
            raise Invalid(
                f"a ceiling of {self.ceiling_ticks} under the "
                f"observed honest maximum of "
                f"{self.honest_maximum} is not a safety net, "
                "it is a lottery"
            )

    def charge(self, action: str, ticks: int) -> str:
        if self.killed:
            raise Invalid("the build is dead; stop charging it")
        if ticks <= 0:
            raise Invalid("actions cost positive ticks")
        self.spent[action] = self.spent.get(action, 0) + ticks
        total = sum(self.spent.values())
        if total > self.ceiling_ticks:
            self.killed = True
            return self.kill_report()
        return f"{action}: {total} of {self.ceiling_ticks}"

    def kill_report(self) -> str:
        total = sum(self.spent.values())
        biggest = max(
            self.spent, key=lambda name: self.spent[name]
        )
        share = 100 * self.spent[biggest] // total
        return (
            f"KILLED at {total} of {self.ceiling_ticks} "
            f"tick(s) across {len(self.spent)} action(s); "
            f"{biggest} spent {share}% of the budget, which "
            "is the difference between a ticket and a fix"
        )
