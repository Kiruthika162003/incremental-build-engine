"""Metric restatements: the meter was wrong, and the history says so twice.

A bug in the cache-hit meter inflated the dashboard for a
quarter, and the tempting fix is to silently repair history,
which converts a measurement bug into a credibility bug the
day someone notices the numbers moved. The restatement keeps
both series: the original readings stand as published, the
recomputed readings stand beside them marked restated with the
defect named, and every consumer sees which series it is
reading, because a chart that cannot say which truth it plots
is not a chart, it is an argument waiting to happen. The
policy has one asymmetry: restating is always allowed,
re-restating requires naming the prior restatement, since a
history rewritten twice without a paper trail is
indistinguishable from a history rewritten for convenience.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class MetricHistory:
    metric: str
    published: dict[str, float] = field(default_factory=dict)
    restated: dict[str, tuple[float, str]] = field(
        default_factory=dict
    )

    def publish(self, period: str, value: float) -> None:
        if period in self.published:
            raise Invalid(
                f"{period} is already published; corrections "
                "go through restatement, not overwriting"
            )
        self.published[period] = value

    def restate(
        self,
        period: str,
        corrected: float,
        defect: str,
        supersedes_note: str = "",
    ) -> str:
        if period not in self.published:
            raise Invalid(
                f"{period} was never published; there is "
                "nothing to restate"
            )
        if not defect.strip():
            raise Invalid(
                "a restatement without a named defect is a "
                "rewrite for convenience"
            )
        if period in self.restated and not supersedes_note:
            raise Invalid(
                f"{period} is already restated; name the prior "
                "restatement or the trail breaks"
            )
        note = defect + (
            f" (supersedes: {supersedes_note})"
            if supersedes_note
            else ""
        )
        self.restated[period] = (corrected, note)
        original = self.published[period]
        return (
            f"{period}: published {original} stands, restated "
            f"{corrected} beside it ({defect})"
        )

    def read(self, period: str) -> str:
        if period not in self.published:
            raise Invalid(f"{period} has no reading")
        original = self.published[period]
        held = self.restated.get(period)
        if held is None:
            return f"{period}: {original} (as published)"
        corrected, note = held
        return (
            f"{period}: {corrected} (RESTATED: {note}; "
            f"originally published {original})"
        )

    def series_label(self) -> str:
        count = len(self.restated)
        if count == 0:
            return f"{self.metric}: as published throughout"
        return (
            f"{self.metric}: {count} of "
            f"{len(self.published)} period(s) restated; both "
            "series survive because a chart that cannot say "
            "which truth it plots is an argument waiting to "
            "happen"
        )
