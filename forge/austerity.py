"""Austerity planning: cut the programs, keep the arithmetic.

When the farm budget shrinks, something optional dies, and the
wrong death is chosen by whoever argues best unless the returns
are on one page. Every optional program, prewarming, hedging,
control groups, the nightly clean room, carries a running cost
and a measured return in the same currency, and the austerity
plan sorts by return per tick spent, drawing the cut line where
the budget lands: programs below the line are suspended with
their ratio printed, programs above survive, and a program
whose return was never measured sorts to the bottom by policy,
because "we think it helps" competes against measured ratios
only in meetings, not in arithmetic. The insurance exception is
explicit: a program flagged as insurance, the clean room, the
control group, is priced by the incident it prevents rather
than the ticks it returns, and the plan refuses to auto-cut
insurance, listing it separately for a human to overrule,
since the cheapest quarter is the one before the fire.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid


@dataclass(frozen=True)
class Program:
    name: str
    cost_per_week: int
    return_per_week: int | None
    insurance: bool = False

    def ratio(self) -> float:
        if self.return_per_week is None:
            return -1.0
        return self.return_per_week / self.cost_per_week


def austerity_plan(
    programs: list[Program], budget_per_week: int
) -> str:
    if not programs:
        raise Invalid("nothing optional to cut")
    if budget_per_week < 0:
        raise Invalid("a negative budget is a shutdown")
    insurance = [p for p in programs if p.insurance]
    cuttable = sorted(
        (p for p in programs if not p.insurance),
        key=lambda p: -p.ratio(),
    )
    kept = []
    suspended = []
    spent = sum(p.cost_per_week for p in insurance)
    for program in cuttable:
        if spent + program.cost_per_week <= budget_per_week:
            spent += program.cost_per_week
            kept.append(program)
        else:
            suspended.append(program)
    lines = [
        f"budget {budget_per_week}/week: {len(kept)} kept, "
        f"{len(suspended)} suspended, {len(insurance)} "
        "insurance held for a human"
    ]
    for program in kept:
        lines.append(
            f"  keep {program.name}: returns "
            f"{program.ratio():.1f} per tick spent"
        )
    for program in suspended:
        note = (
            "never measured, sorted last by policy"
            if program.return_per_week is None
            else f"returns {program.ratio():.1f}"
        )
        lines.append(f"  suspend {program.name}: {note}")
    for program in insurance:
        lines.append(
            f"  insurance {program.name}: priced by the "
            "incident it prevents, not the ticks it returns; "
            "auto-cutting it buys the cheapest quarter before "
            "the fire"
        )
    return "\n".join(lines)
