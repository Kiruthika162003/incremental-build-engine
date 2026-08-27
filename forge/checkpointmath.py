"""Checkpoint intervals: save too often and the saving is the cost.

A long action on preemptible hardware loses its progress since
the last checkpoint every time the machine vanishes, so
checkpoints exist; but every checkpoint pays its own overhead
whether or not a preemption ever comes, so checkpointing every
tick is a different way to burn the discount. The expected bill
for a run is overhead times the number of checkpoints plus, per
expected preemption, half an interval of lost work and the
restore fee, and the interval that minimizes it follows the
square-root law: the optimum grows with checkpoint cost and
shrinks with preemption rate, which is why the right interval
for a quiet fleet is long and for a stormy one is short. The
planner evaluates the candidate intervals directly rather than
trusting the formula, and reports both, because the closed form
assumes smooth arrivals and the honest table sometimes
disagrees with it by a slot, and the table is the one that
paid.
"""

from __future__ import annotations

from forge.errors import Invalid


def expected_bill(
    run_ticks: int,
    interval: int,
    checkpoint_cost: int,
    restore_cost: int,
    preemptions_per_run: float,
) -> float:
    if interval <= 0 or interval > run_ticks:
        raise Invalid(
            "the interval must be positive and no longer than "
            "the run"
        )
    checkpoints = run_ticks // interval
    overhead = checkpoints * checkpoint_cost
    loss_per_preemption = interval / 2 + restore_cost
    return overhead + preemptions_per_run * loss_per_preemption


def sqrt_law_interval(
    checkpoint_cost: int, preemption_rate_per_tick: float
) -> float:
    if preemption_rate_per_tick <= 0:
        raise Invalid(
            "with no preemptions the best interval is the whole "
            "run; the law divides by the rate"
        )
    return (2 * checkpoint_cost / preemption_rate_per_tick) ** 0.5


def plan(
    run_ticks: int,
    checkpoint_cost: int,
    restore_cost: int,
    preemptions_per_run: float,
    candidates: list[int],
) -> str:
    if not candidates:
        raise Invalid("no intervals to evaluate")
    table = sorted(
        (
            expected_bill(
                run_ticks,
                interval,
                checkpoint_cost,
                restore_cost,
                preemptions_per_run,
            ),
            interval,
        )
        for interval in candidates
    )
    best_bill, best_interval = table[0]
    rate = preemptions_per_run / run_ticks
    law = sqrt_law_interval(checkpoint_cost, rate)
    agreement = (
        "the table agrees with the law"
        if abs(best_interval - law) <= min(
            abs(candidate - law) for _, candidate in table
        )
        else "the table overrules the smooth-arrival law"
    )
    return (
        f"checkpoint every {best_interval} tick(s) for an "
        f"expected bill of {best_bill:.0f}; the square-root law "
        f"says {law:.0f}, and {agreement}"
    )
