"""Thermal scheduling: the laptop that sprints and rests beats the one that pins.

A build farm's worker holds its clock speed all day; a laptop
does not, and scheduling for one as if it were the other is
how eight cores deliver four cores of work. The model is
blunt: sustained full load heats the package until it
throttles to a fraction of its speed, and cooling only happens
below the load threshold, so the pin-everything strategy runs
the first minutes fast and the rest of the hour slow. The
sprint-and-rest schedule alternates full load with cool-down
gaps, stays under the throttle ceiling, and wins on the hour
despite doing nothing during the rests, which is the
counterintuitive result the simulator exists to show with
numbers rather than assert with vibes. The report prints both
hours side by side, because a developer told to use fewer
cores hears nonsense until the ledger shows the throttled
hour losing to the rested one.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid

HEAT_PER_LOADED_TICK = 4
COOL_PER_RESTED_TICK = 6
THROTTLE_AT = 100
THROTTLED_SPEED = 0.4


@dataclass
class ThermalSim:
    heat: int = 0
    work_done: float = 0.0
    throttled_ticks: int = 0

    def tick(self, loaded: bool) -> None:
        if loaded:
            throttled = self.heat >= THROTTLE_AT
            self.work_done += (
                THROTTLED_SPEED if throttled else 1.0
            )
            if throttled:
                self.throttled_ticks += 1
            self.heat += HEAT_PER_LOADED_TICK
        else:
            self.heat = max(0, self.heat - COOL_PER_RESTED_TICK)


def run_schedule(pattern: list[bool]) -> ThermalSim:
    if not pattern:
        raise Invalid("an empty schedule builds nothing")
    sim = ThermalSim()
    for loaded in pattern:
        sim.tick(loaded)
    return sim


def pin_everything(ticks: int) -> ThermalSim:
    return run_schedule([True] * ticks)


def sprint_and_rest(
    ticks: int, sprint: int, rest: int
) -> ThermalSim:
    if sprint < 1 or rest < 1:
        raise Invalid("sprints and rests need positive lengths")
    pattern = []
    while len(pattern) < ticks:
        pattern.extend([True] * sprint)
        pattern.extend([False] * rest)
    return run_schedule(pattern[:ticks])


def hour_report(ticks: int, sprint: int, rest: int) -> str:
    pinned = pin_everything(ticks)
    rested = sprint_and_rest(ticks, sprint, rest)
    winner = (
        "sprint-and-rest"
        if rested.work_done > pinned.work_done
        else "pin-everything"
    )
    return (
        f"over {ticks} tick(s): pin-everything did "
        f"{pinned.work_done:.0f} work with "
        f"{pinned.throttled_ticks} throttled tick(s); "
        f"sprint {sprint}/rest {rest} did "
        f"{rested.work_done:.0f} with "
        f"{rested.throttled_ticks}; {winner} wins, and the "
        "rests did nothing except everything"
    )
