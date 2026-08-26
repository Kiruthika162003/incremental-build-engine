"""Progress estimation: the bar should apologise when it lies.

A build's remaining time is a prediction from a cost model, and
cost models drift: the checked-in cost says 5 and the machine says
9 today because the machine is thermal throttling. The estimator
starts from modeled costs, corrects per completed action with an
exponentially weighted speed factor, and re-projects the remaining
work through the corrected factor on every completion, so the bar
bends toward truth as evidence arrives. Every finished build then
grades its own forecast: the error curve records what the bar
promised at each completion against what actually remained, and
the honesty line reports the worst overpromise, because a progress
bar that says almost-done for the last half of the build teaches
people to alt-tab, and the number that fixes that habit is the
error, printed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

SMOOTHING = 0.4


@dataclass
class ProgressModel:
    modeled: dict[str, int]
    speed_factor: float = 1.0
    completed: dict[str, int] = field(default_factory=dict)
    promises: list[tuple[int, float]] = field(default_factory=list)
    elapsed: int = 0

    def __post_init__(self) -> None:
        if not self.modeled:
            raise Invalid("a progress model needs modeled costs")
        if any(cost <= 0 for cost in self.modeled.values()):
            raise Invalid("modeled costs must be positive")

    def remaining_estimate(self) -> float:
        left = sum(
            cost
            for name, cost in self.modeled.items()
            if name not in self.completed
        )
        return round(left * self.speed_factor, 2)

    def finish(self, name: str, actual: int) -> None:
        if name not in self.modeled:
            raise Invalid(f"{name} is not in the model")
        if name in self.completed:
            raise Invalid(f"{name} already finished")
        self.completed[name] = actual
        self.elapsed += actual
        observed = actual / self.modeled[name]
        self.speed_factor = round(
            (1 - SMOOTHING) * self.speed_factor + SMOOTHING * observed, 4
        )
        self.promises.append((self.elapsed, self.remaining_estimate()))

    def error_curve(self) -> list[tuple[int, float]]:
        if len(self.completed) < len(self.modeled):
            raise Invalid("the build has not finished; grade it later")
        total = self.elapsed
        curve = []
        for at_tick, promised in self.promises:
            actual_remaining = total - at_tick
            curve.append(
                (at_tick, round(promised - actual_remaining, 2))
            )
        return curve

    def honesty_line(self) -> str:
        curve = self.error_curve()
        if not curve:
            return "no promises were made"
        worst = min(curve, key=lambda row: row[1])
        best = max(curve, key=lambda row: row[1])
        return (
            f"worst overpromise {worst[1]} at tick {worst[0]}, "
            f"worst underpromise +{best[1]} at tick {best[0]}"
        )
