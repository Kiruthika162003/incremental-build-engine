"""Spot instance arithmetic: cheap workers that vanish are cheap sometimes.

Spot capacity sells at a deep discount because it can be yanked
mid-action, and whether the discount survives contact depends on
one ratio: how much work a preemption throws away against how
much the discount saves. The model prices a day honestly: every
preemption costs the ticks the dead action had accrued plus the
scheduling gap before a replacement, and the verdict compares
the spot bill with the on-demand bill for the same completed
work. The interesting output is the break-even preemption rate,
computed, not felt, because teams argue "spot is flaky" against
"spot is cheap" forever, and the argument ends when someone
prints the rate at which the two bills cross next to the rate
the fleet actually observes. Checkpointing shifts the math and
the model says by how much: saved progress turns a preemption
from a restart into a resume, which moves the break-even, and
the delta is the entire business case for checkpoint support.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid


@dataclass(frozen=True)
class SpotDay:
    actions: int
    ticks_per_action: int
    on_demand_rate: float
    spot_discount: float
    preemptions: int
    respawn_gap_ticks: int
    checkpointed: bool = False

    def __post_init__(self) -> None:
        if not 0 < self.spot_discount < 1:
            raise Invalid(
                "the discount is a fraction strictly between "
                "0 and 1"
            )
        if self.preemptions > self.actions:
            raise Invalid(
                "more preemptions than actions means the fleet "
                "is not building, it is flickering"
            )

    def useful_ticks(self) -> int:
        return self.actions * self.ticks_per_action

    def wasted_ticks(self) -> int:
        lost_progress = (
            0
            if self.checkpointed
            else self.preemptions * (self.ticks_per_action // 2)
        )
        return lost_progress + (
            self.preemptions * self.respawn_gap_ticks
        )

    def spot_bill(self) -> float:
        rate = self.on_demand_rate * (1 - self.spot_discount)
        return rate * (self.useful_ticks() + self.wasted_ticks())

    def on_demand_bill(self) -> float:
        return self.on_demand_rate * self.useful_ticks()

    def break_even_preemptions(self) -> int:
        overhead_per_preemption = self.respawn_gap_ticks + (
            0
            if self.checkpointed
            else self.ticks_per_action // 2
        )
        if overhead_per_preemption == 0:
            raise Invalid(
                "free preemptions have no break-even; spot "
                "always wins"
            )
        rate = 1 - self.spot_discount
        budget = self.useful_ticks() * (1 / rate - 1)
        return int(budget // overhead_per_preemption)

    def verdict(self) -> str:
        spot = self.spot_bill()
        demand = self.on_demand_bill()
        breakeven = self.break_even_preemptions()
        mode = (
            "with checkpoints"
            if self.checkpointed
            else "without checkpoints"
        )
        if spot < demand:
            return (
                f"spot wins {mode}: {spot:.0f} against "
                f"{demand:.0f}, {self.preemptions} preemption(s) "
                f"observed against a break-even of {breakeven}"
            )
        return (
            f"on-demand wins {mode}: the fleet observed "
            f"{self.preemptions} preemption(s) against a "
            f"break-even of {breakeven}, and the discount "
            f"drowned in rework ({spot:.0f} vs {demand:.0f})"
        )
