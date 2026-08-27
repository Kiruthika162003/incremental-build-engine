"""Fault lines: the farm's single points of failure, named by subtraction.

Redundancy reports flatter fleets, forty workers, three
regions, until someone asks which single loss actually hurts,
and the honest answer comes from subtraction: remove each pool
in turn and count the action classes that become unmatchable.
A pool whose removal strands nothing is capacity; a pool whose
removal strands work is a fault line, and the one mac pool with
the signing identity usually turns out to be the whole release
process standing on one power supply. The report ranks pools
by stranded demand, prices the fix as the second pool the
ranking argues for, and refuses the comfortable summary: a
farm is as redundant as its most necessary pool, not as its
average one.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid
from forge.workermatch import Matcher, Pool


@dataclass
class FaultLineReport:
    pools: list[Pool]
    demand_classes: dict[str, dict[str, str]]

    def _matchable(
        self, pools: list[Pool], demands: dict[str, str]
    ) -> bool:
        if not pools:
            return False
        matcher = Matcher()
        for pool in pools:
            matcher.add_pool(pool)
        try:
            matcher.match(demands)
        except Invalid:
            return False
        return True

    def stranded_by(self, pool_name: str) -> list[str]:
        if not any(
            pool.name == pool_name for pool in self.pools
        ):
            raise Invalid(f"{pool_name} is not on this farm")
        remaining = [
            pool
            for pool in self.pools
            if pool.name != pool_name
        ]
        return sorted(
            demand_name
            for demand_name, demands in self.demand_classes.items()
            if self._matchable(self.pools, demands)
            and not self._matchable(remaining, demands)
        )

    def report(self) -> str:
        if not self.demand_classes:
            raise Invalid("no demand to strand")
        rows = []
        for pool in self.pools:
            stranded = self.stranded_by(pool.name)
            rows.append((len(stranded), pool.name, stranded))
        rows.sort(reverse=True)
        worst_count, worst_name, worst_stranded = rows[0]
        lines = []
        if worst_count == 0:
            lines.append(
                "no single pool loss strands anything; the "
                "redundancy is real"
            )
        else:
            lines.append(
                f"the fault line is {worst_name}: losing it "
                f"strands {', '.join(worst_stranded)}; the fix "
                f"is a second pool with {worst_name}'s "
                "properties"
            )
        for count, name, stranded in rows:
            label = (
                f"fault line ({', '.join(stranded)})"
                if count
                else "capacity"
            )
            lines.append(f"  {name}: {label}")
        lines.append(
            "a farm is as redundant as its most necessary "
            "pool, not as its average one"
        )
        return "\n".join(lines)
