"""Hedged actions: pay a little duplicate work to amputate the tail.

The farm's median worker finishes in 10 ticks and its worst
straggles to 90, and a build of a thousand actions meets that
tail often enough to be scheduled around it. The hedge sends a
second copy of an action to a different worker after a delay,
takes whichever answer lands first, and cancels the loser; the
duplicate work is real and the tail amputation is real, and the
policy is only as good as the arithmetic between them. The
simulator runs a latency profile through a hedge delay and
reports both currencies, completion of the slowest action
against duplicate ticks burned, plus the break-even question
answered directly: the delay below which hedging burns more than
it saves on this profile. A hedge that fires never is free and
useless; one that fires always doubles the farm; the interesting
delays live between, and the report names the one that minimizes
the sum.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid


@dataclass(frozen=True)
class HedgeOutcome:
    finish: int
    duplicate_ticks: int
    hedge_fired: bool
    hedge_won: bool


def run_action(
    primary_ticks: int, backup_ticks: int, delay: int
) -> HedgeOutcome:
    if primary_ticks <= 0 or backup_ticks <= 0 or delay < 0:
        raise Invalid(
            "latencies must be positive and the delay nonnegative"
        )
    if primary_ticks <= delay:
        return HedgeOutcome(
            finish=primary_ticks,
            duplicate_ticks=0,
            hedge_fired=False,
            hedge_won=False,
        )
    backup_finish = delay + backup_ticks
    finish = min(primary_ticks, backup_finish)
    hedge_won = backup_finish < primary_ticks
    loser_started_at = 0 if hedge_won else delay
    return HedgeOutcome(
        finish=finish,
        duplicate_ticks=finish - loser_started_at,
        hedge_fired=True,
        hedge_won=hedge_won,
    )


@dataclass
class HedgePolicy:
    delay: int

    def simulate(
        self, profile: list[tuple[int, int]]
    ) -> tuple[int, int, int]:
        if not profile:
            raise Invalid("no actions to simulate")
        worst = 0
        duplicates = 0
        fired = 0
        for primary, backup in profile:
            outcome = run_action(primary, backup, self.delay)
            worst = max(worst, outcome.finish)
            duplicates += outcome.duplicate_ticks
            fired += 1 if outcome.hedge_fired else 0
        return worst, duplicates, fired


def best_delay(
    profile: list[tuple[int, int]], candidates: list[int]
) -> str:
    if not candidates:
        raise Invalid("no delays to try")
    scored = []
    for delay in sorted(candidates):
        worst, duplicates, fired = HedgePolicy(
            delay=delay
        ).simulate(profile)
        scored.append((worst + duplicates, delay, worst, duplicates, fired))
    scored.sort()
    total, delay, worst, duplicates, fired = scored[0]
    return (
        f"delay {delay}: slowest action {worst}, duplicate "
        f"{duplicates}, hedges fired {fired}, combined {total} "
        "(the minimum over the candidates)"
    )
