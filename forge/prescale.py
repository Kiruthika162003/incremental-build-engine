"""Calendar prescaling: Monday at ten is not a surprise, stop treating it like one.

Reactive autoscaling answers a burst after developers are
already waiting, which is the right tool for surprises and the
wrong one for rush hour. The prescaler learns the weekly shape
from history, one expected depth per hour slot averaged across
observed weeks, and raises the fleet's floor ahead of the
slots history calls busy, so the reactive layer only has to
handle what the calendar could not know. The division of labor
is measured, not asserted: the report splits demand into
calendar-served and reaction-served, because a prescaler
claiming credit for the whole morning is stealing valor from
the burst handler, and one serving nothing is a spreadsheet
wearing an SLA. Learning is honest about thin history, a slot
seen once carries its count and a low-confidence mark, since
one loud Monday does not make a season.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

CONFIDENT_WEEKS = 3


@dataclass
class Prescaler:
    depth_per_worker: int
    history: dict[int, list[int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.depth_per_worker < 1:
            raise Invalid("depth per worker must be positive")

    def observe_week(self, depths_by_slot: dict[int, int]) -> None:
        if not depths_by_slot:
            raise Invalid("an empty week teaches nothing")
        for slot, depth in depths_by_slot.items():
            if not 0 <= slot < 168:
                raise Invalid(
                    f"slot {slot} is not an hour of the week"
                )
            self.history.setdefault(slot, []).append(depth)

    def floor_for(self, slot: int) -> tuple[int, str]:
        seen = self.history.get(slot, [])
        if not seen:
            return 0, "no history; the reactive layer owns this slot"
        expected = sum(seen) / len(seen)
        floor = int(expected) // self.depth_per_worker
        confidence = (
            "confident"
            if len(seen) >= CONFIDENT_WEEKS
            else f"low confidence ({len(seen)} week(s))"
        )
        return floor, confidence

    def serve_slot(self, slot: int, actual_depth: int) -> str:
        floor, confidence = self.floor_for(slot)
        calendar_served = min(
            actual_depth, floor * self.depth_per_worker
        )
        reaction_served = actual_depth - calendar_served
        return (
            f"slot {slot}: floor {floor} worker(s) "
            f"({confidence}); calendar served "
            f"{calendar_served}, reaction served "
            f"{reaction_served}"
        )

    def week_report(
        self, actuals: dict[int, int]
    ) -> str:
        if not actuals:
            raise Invalid("no actuals to grade")
        calendar_total = 0
        reaction_total = 0
        for slot, depth in sorted(actuals.items()):
            floor, _ = self.floor_for(slot)
            served = min(depth, floor * self.depth_per_worker)
            calendar_total += served
            reaction_total += depth - served
        return (
            f"calendar served {calendar_total}, reaction "
            f"served {reaction_total}; a prescaler claiming the "
            "whole morning is stealing valor, one serving "
            "nothing is a spreadsheet wearing an SLA"
        )
