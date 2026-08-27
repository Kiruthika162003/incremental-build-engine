"""Reformatting the fleet: one loud day or a thousand quiet ones.

Adopting a formatter poses one real question, and it is not
about style: big-bang reformats every file in one commit,
paying a day of frozen merges and a permanent seam in blame,
after which the tree is uniform forever; touch-style formats
only files edited after the flag day, costing nothing up front
and converging asymptotically, which means never, because cold
files are cold precisely because nobody touches them. The
simulator runs both policies over the same edit pattern and
reports the shape teams misjudge: touch-style covers the hot
half of the tree in weeks and then flatlines, so the honest
policy is the hybrid the report recommends, touch-style plus a
scheduled sweep of the cold remainder once the noise argument
has expired, with the blame seam paid in one commit per cold
directory instead of one per fleet.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class ReformatSim:
    files: int
    hot_files: int
    formatted: set[int] = field(default_factory=set)
    weeks: int = 0

    def __post_init__(self) -> None:
        if not 0 < self.hot_files <= self.files:
            raise Invalid(
                "hot files must be between 1 and the tree size"
            )

    def big_bang(self) -> str:
        self.formatted = set(range(self.files))
        return (
            f"{self.files} file(s) in one commit: a day of "
            "frozen merges, a permanent seam in blame, and "
            "uniformity forever"
        )

    def week_of_touches(self) -> None:
        self.weeks += 1
        touched = {
            (self.weeks * 7 + offset) % self.hot_files
            for offset in range(self.hot_files // 4)
        }
        self.formatted.update(touched)

    def coverage(self) -> float:
        return len(self.formatted) / self.files

    def convergence_report(self, weeks: int) -> str:
        for _ in range(weeks):
            self.week_of_touches()
        hot_covered = len(
            [f for f in self.formatted if f < self.hot_files]
        )
        cold_covered = len(self.formatted) - hot_covered
        return (
            f"after {weeks} week(s): {self.coverage():.0%} of "
            f"the tree, {hot_covered} of {self.hot_files} hot "
            f"file(s), {cold_covered} of "
            f"{self.files - self.hot_files} cold; the curve "
            "flatlines here because cold files are cold "
            "precisely because nobody touches them"
        )


def policy_advice(
    files: int, hot_files: int, weeks_observed: int
) -> str:
    sim = ReformatSim(files=files, hot_files=hot_files)
    report = sim.convergence_report(weeks_observed)
    cold = files - hot_files
    return (
        report
        + "\n"
        + (
            f"hybrid: keep touch-style for the hot set and "
            f"sweep the {cold} cold file(s) on a schedule, one "
            "commit per cold directory instead of one per fleet"
        )
    )
