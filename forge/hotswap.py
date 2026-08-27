"""Hot swap or restart: the dev server's question, answered by digests.

A development server that restarts on every save wastes the
developer's rhythm; one that hot-swaps changes it cannot swap
serves stale behavior, which is worse, because a wrong page
outranks a slow one on every incident review. The gate reuses the
interface split: a body-only edit swaps in place, an interface
change restarts, and anything touching module-level state
restarts too, since a swapped module keeps the old state alive
next to the new code and that hybrid is the classic unreproducible
bug. The session ledger counts swaps, restarts, and the saves
that needed nothing, then prices the rhythm: swaps cost one tick,
restarts twelve, and the ledger shows what the gate saved against
the restart-everything baseline the team started from.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid
from forge.symbolselect import SourceUnit

SWAP_TICKS = 1
RESTART_TICKS = 12


@dataclass
class HotSession:
    units: dict[str, SourceUnit] = field(default_factory=dict)
    stateful: set[str] = field(default_factory=set)
    swaps: int = 0
    restarts: int = 0
    quiet_saves: int = 0
    ticks_paid: int = 0

    def admit(
        self, unit: SourceUnit, holds_state: bool = False
    ) -> None:
        self.units[unit.path] = unit
        if holds_state:
            self.stateful.add(unit.path)

    def save(self, unit: SourceUnit) -> str:
        held = self.units.get(unit.path)
        if held is None:
            raise Invalid(
                f"{unit.path} is not part of the session"
            )
        if unit.full_digest() == held.full_digest():
            self.quiet_saves += 1
            return f"{unit.path}: nothing moved, nothing to do"
        self.units[unit.path] = unit
        if unit.path in self.stateful:
            self.restarts += 1
            self.ticks_paid += RESTART_TICKS
            return (
                f"{unit.path}: restart; swapped code next to old "
                "state is the classic unreproducible bug"
            )
        if unit.interface_digest() != held.interface_digest():
            self.restarts += 1
            self.ticks_paid += RESTART_TICKS
            return (
                f"{unit.path}: restart; the public face moved and "
                "importers hold the old one"
            )
        self.swaps += 1
        self.ticks_paid += SWAP_TICKS
        return f"{unit.path}: hot swap, body only"

    def rhythm_bill(self) -> str:
        events = self.swaps + self.restarts
        baseline = events * RESTART_TICKS
        saved = baseline - self.ticks_paid
        return (
            f"{self.swaps} swap(s), {self.restarts} restart(s), "
            f"{self.quiet_saves} quiet save(s): paid "
            f"{self.ticks_paid} ticks where restart-everything "
            f"pays {baseline}, saving {saved}"
        )
