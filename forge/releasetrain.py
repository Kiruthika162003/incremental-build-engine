"""The release train leaves on time; the fix takes the next one.

Release branches cut on a schedule turn "is it ready" from a
negotiation into a calendar fact, and everything after the cut is
a cherry-pick with a burden of proof. The train models that
burden as a shrinking gate: early in stabilization a fix needs
one approval, late it needs two and a named risk, and after the
freeze only a showstopper boards at all, because the closer the
departure the more a change endangers the passengers already
aboard. Every boarding and every refusal is logged with the
phase it happened in, and the manifest the train departs with is
the release note nobody has to reconstruct: what was cut, what
boarded late and why, and what was turned away to catch the
next train.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

PHASES = ("open", "stabilizing", "frozen")


@dataclass(frozen=True)
class CherryPick:
    fix: str
    approvals: int
    risk_note: str = ""
    showstopper: bool = False


@dataclass
class ReleaseTrain:
    version: str
    cut_commit: str
    phase: str = "open"
    boarded: list[str] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)

    def advance(self) -> str:
        position = PHASES.index(self.phase)
        if position == len(PHASES) - 1:
            raise Invalid(
                f"{self.version} is already frozen; the next "
                "phase is the platform"
            )
        self.phase = PHASES[position + 1]
        return f"{self.version} enters {self.phase}"

    def request(self, pick: CherryPick) -> str:
        verdict = self._grade(pick)
        if verdict is None:
            self.boarded.append(
                f"{pick.fix} boarded during {self.phase}"
                + (
                    f" (risk: {pick.risk_note})"
                    if pick.risk_note
                    else ""
                )
            )
            return f"{pick.fix} boards the {self.version} train"
        self.refused.append(
            f"{pick.fix} refused during {self.phase}: {verdict}"
        )
        return (
            f"{pick.fix} takes the next train: {verdict}"
        )

    def _grade(self, pick: CherryPick) -> str | None:
        if self.phase == "open":
            if pick.approvals >= 1:
                return None
            return "even the open train wants one approval"
        if self.phase == "stabilizing":
            if pick.approvals < 2:
                return (
                    f"stabilizing wants two approvals, got "
                    f"{pick.approvals}"
                )
            if not pick.risk_note:
                return (
                    "stabilizing wants the risk written down, "
                    "not remembered"
                )
            return None
        if pick.showstopper and pick.approvals >= 2:
            return None
        return (
            "the train is frozen; only a showstopper with two "
            "approvals boards"
        )

    def manifest(self) -> str:
        lines = [
            f"{self.version} cut at {self.cut_commit} "
            f"(phase: {self.phase})"
        ]
        lines.append(f"boarded: {len(self.boarded)}")
        lines.extend(f"  {entry}" for entry in self.boarded)
        lines.append(f"turned away: {len(self.refused)}")
        lines.extend(f"  {entry}" for entry in self.refused)
        return "\n".join(lines)
