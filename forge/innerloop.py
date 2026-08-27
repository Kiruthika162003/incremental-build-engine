"""The inner loop metric: how long until the developer knows.

The only build latency that shapes behavior is the one between
saving a file and learning whether it worked, and its
distribution is almost always bimodal: two seconds when the
cache catches the edit, ninety when it does not, and no
developer ever experiences the fifty-second mean that dashboards
report. The tracker records edit-to-feedback samples and refuses
the single-number summary on a bimodal day, reporting the two
modes separately with their populations, because a team told
"p50 is fine" while every fourth edit costs ninety seconds will
correctly stop believing the dashboard. The flow verdict is the
behavioral read: under the flow threshold developers stay in the
editor, over the abandonment threshold they context-switch, and
the fraction of edits past that cliff is the number that
predicts how often people tab over to something else and do not
come back.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

FLOW_TICKS = 10
ABANDON_TICKS = 60
MODE_GAP = 5


@dataclass
class InnerLoop:
    samples: list[int] = field(default_factory=list)

    def record(self, ticks: int) -> None:
        if ticks <= 0:
            raise Invalid("feedback cannot arrive before the edit")
        self.samples.append(ticks)

    def _modes(self) -> list[list[int]]:
        if not self.samples:
            raise Invalid("no edits recorded")
        ordered = sorted(self.samples)
        clusters = [[ordered[0]]]
        for sample in ordered[1:]:
            if sample - clusters[-1][-1] <= MODE_GAP:
                clusters[-1].append(sample)
            else:
                clusters.append([sample])
        return clusters

    def summary(self) -> str:
        clusters = self._modes()
        mean = sum(self.samples) / len(self.samples)
        if len(clusters) == 1:
            return (
                f"unimodal: {len(self.samples)} edit(s) around "
                f"{mean:.0f} tick(s); the mean is honest today"
            )
        parts = []
        for cluster in clusters:
            center = sum(cluster) / len(cluster)
            parts.append(
                f"{len(cluster)} edit(s) near {center:.0f}"
            )
        return (
            f"bimodal at least: {', '.join(parts)}; the "
            f"{mean:.0f}-tick mean describes nobody's edit"
        )

    def flow_verdict(self) -> str:
        total = len(self.samples)
        if total == 0:
            raise Invalid("no edits recorded")
        in_flow = sum(
            1 for sample in self.samples if sample <= FLOW_TICKS
        )
        abandoned = sum(
            1 for sample in self.samples if sample > ABANDON_TICKS
        )
        return (
            f"{in_flow} of {total} edit(s) kept flow "
            f"(<= {FLOW_TICKS}), {abandoned} crossed the "
            f"abandonment cliff (> {ABANDON_TICKS}): that is "
            f"{100 * abandoned // total}% of edits losing the "
            "developer"
        )
