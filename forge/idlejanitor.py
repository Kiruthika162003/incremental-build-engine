"""The idle janitor: maintenance fills the gaps and yields the hallway.

An idle worker is not free capacity, it is capacity nobody has
claimed yet, and the janitor's contract is built around that
distinction: maintenance chores, cache warming, flake
certification, clean-room slices, run only in idle gaps and
yield immediately when real work arrives, with the interrupted
chore requeued at its front, not restarted, because a chore
that loses its progress to every arrival never finishes on a
busy farm. Chores carry priorities of their own, insurance
before convenience, and the ledger reports the week the way an
honest janitor would: chores finished, chores standing aside,
and the tick that matters most, how long real work waited for
the hallway, which must be zero, since a janitor that ever
delays the business is a janitor for one more week.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class Chore:
    name: str
    ticks_left: int
    insurance: bool = False


@dataclass
class IdleJanitor:
    chores: list[Chore] = field(default_factory=list)
    finished: list[str] = field(default_factory=list)
    yields: int = 0
    real_work_wait_ticks: int = 0
    idle_ticks_used: int = 0

    def add_chore(
        self, name: str, ticks: int, insurance: bool = False
    ) -> None:
        if ticks <= 0:
            raise Invalid(f"{name} is already done")
        self.chores.append(
            Chore(name=name, ticks_left=ticks, insurance=insurance)
        )
        self.chores.sort(
            key=lambda chore: (not chore.insurance, chore.name)
        )

    def idle_gap(self, ticks: int) -> str:
        if ticks <= 0:
            raise Invalid("a gap needs ticks")
        remaining = ticks
        worked_on = []
        while remaining > 0 and self.chores:
            chore = self.chores[0]
            spent = min(remaining, chore.ticks_left)
            chore.ticks_left -= spent
            remaining -= spent
            self.idle_ticks_used += spent
            worked_on.append(f"{chore.name} ({spent})")
            if chore.ticks_left == 0:
                self.finished.append(chore.name)
                self.chores.pop(0)
        if not worked_on:
            return "no chores; the gap stays idle"
        return f"gap of {ticks}: " + ", ".join(worked_on)

    def real_work_arrives(self) -> str:
        self.yields += 1
        if not self.chores:
            return "the hallway was already clear"
        front = self.chores[0]
        return (
            f"{front.name} yields immediately with "
            f"{front.ticks_left} tick(s) kept, requeued at its "
            "front, not restarted"
        )

    def week_ledger(self) -> str:
        standing = ", ".join(
            chore.name for chore in self.chores
        ) or "none"
        return (
            f"{len(self.finished)} chore(s) finished using "
            f"{self.idle_ticks_used} idle tick(s), "
            f"{self.yields} yield(s), standing aside: "
            f"{standing}; real work waited "
            f"{self.real_work_wait_ticks} tick(s), and that "
            "number being zero is the janitor's whole contract"
        )
