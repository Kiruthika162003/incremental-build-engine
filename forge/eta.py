"""Queue ETAs: a promise with an error bar, or no promise at all.

"Your build starts soon" is the least useful sentence a queue
can say, and a falsely precise "starts in 90 seconds" is worse,
because developers plan around it and learn contempt when it
lies. The estimator predicts start time from the work ahead in
the queue divided by drain rate, and every promise carries its
own error bar computed from the estimator's recent record,
wide when the queue has been erratic, narrow when it has been
steady. The honesty loop is the feature: each prediction is
scored against the actual start, the rolling error updates the
next error bar, and the report grades the estimator in public,
under-promising and over-promising counted separately, because
a queue that always starts builds earlier than promised is
also lying, just politely, and planning suffers either way.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

RECORD_WINDOW = 5


@dataclass
class EtaEstimator:
    drain_per_tick: int
    errors: list[int] = field(default_factory=list)
    early: int = 0
    late: int = 0

    def __post_init__(self) -> None:
        if self.drain_per_tick < 1:
            raise Invalid("a queue that never drains has no ETA")

    def error_bar(self) -> int:
        if not self.errors:
            return 0
        recent = self.errors[-RECORD_WINDOW:]
        return max(abs(error) for error in recent)

    def promise(self, work_ahead: int) -> str:
        if work_ahead < 0:
            raise Invalid("work ahead cannot be negative")
        estimate = work_ahead // self.drain_per_tick
        bar = self.error_bar()
        if bar == 0:
            return (
                f"starts in ~{estimate} tick(s) (no record "
                "yet; treat the number gently)"
            )
        return f"starts in {estimate} +/- {bar} tick(s)"

    def score(self, promised: int, actual: int) -> str:
        error = actual - promised
        self.errors.append(error)
        if error > 0:
            self.late += 1
            return (
                f"late by {error}: the next error bar widens "
                "to cover it"
            )
        if error < 0:
            self.early += 1
            return (
                f"early by {-error}: polite, but still a lie "
                "planning suffered for"
            )
        return "exact; the estimator earns a narrower bar"

    def public_grade(self) -> str:
        if not self.errors:
            raise Invalid("no promises scored yet")
        exact = len(self.errors) - self.early - self.late
        return (
            f"{len(self.errors)} promise(s): {exact} exact, "
            f"{self.early} early, {self.late} late; current "
            f"error bar {self.error_bar()} tick(s), graded in "
            "public because contempt is compounding"
        )
