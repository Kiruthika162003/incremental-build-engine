"""Preflight: the two-tick check that saves the ninety-tick round trip.

Submitting a broken change to the farm costs a queue slot, a
worker lease, and a round trip before the failure comes back,
and most of those failures were knowable at the desk: a parse
error, an undeclared dependency, a graph cycle. The preflight
runs the cheap checks locally in a fixed order, cheapest first,
and stops at the first failure, because the second error behind
a parse failure is usually the parse failure wearing a
different line number. The economics are metered rather than
asserted: every desk-caught failure banks the round trip it
avoided, every clean preflight pays its own small toll, and the
ledger reports the balance, because a preflight that rarely
catches anything on a team that rarely breaks is honest
overhead and should be allowed to say so.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from forge.errors import Invalid

Check = tuple[str, int, Callable[[], str | None]]
ROUND_TRIP_TICKS = 90


@dataclass
class Preflight:
    checks: list[Check] = field(default_factory=list)
    desk_catches: int = 0
    clean_runs: int = 0
    toll_paid: int = 0
    round_trips_banked: int = 0

    def add_check(
        self,
        name: str,
        cost_ticks: int,
        run: Callable[[], str | None],
    ) -> None:
        if cost_ticks <= 0:
            raise Invalid(f"{name} needs a positive cost")
        self.checks.append((name, cost_ticks, run))
        self.checks.sort(key=lambda check: (check[1], check[0]))

    def run(self) -> str:
        if not self.checks:
            raise Invalid("a preflight with no checks checks nothing")
        spent = 0
        for name, cost, run in self.checks:
            spent += cost
            self.toll_paid += cost
            error = run()
            if error is not None:
                self.desk_catches += 1
                self.round_trips_banked += ROUND_TRIP_TICKS
                return (
                    f"CAUGHT AT THE DESK by {name} after "
                    f"{spent} tick(s): {error}; the farm never "
                    "sees this one"
                )
        self.clean_runs += 1
        return f"clean after {spent} tick(s); submit"

    def ledger(self) -> str:
        balance = self.round_trips_banked - self.toll_paid
        if balance >= 0:
            return (
                f"{self.desk_catches} desk catch(es) banked "
                f"{self.round_trips_banked} tick(s) against a "
                f"toll of {self.toll_paid}: the preflight earns "
                f"{balance}"
            )
        return (
            f"{self.clean_runs} clean run(s), "
            f"{self.desk_catches} catch(es): the toll of "
            f"{self.toll_paid} exceeds the "
            f"{self.round_trips_banked} banked; honest overhead "
            "on a team that rarely breaks, and allowed to say so"
        )
