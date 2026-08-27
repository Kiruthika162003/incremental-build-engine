"""Promotion ladders: bits do not rebuild between environments, they promote.

The oldest deployment bug is the rebuild-per-environment: the
binary tested in staging and the binary shipped to production
were built from the same commit, and are still not the same
binary, because a dependency moved or a stamp differed, and the
test coverage silently applied to bits nobody deployed. The
ladder makes identity the rule: an artifact enters at the bottom
rung with its digest, and every promotion re-presents that digest
and moves the same bits up one rung, never skipping, never
rebuilding, so what runs in production is provably the bytes that
survived staging. Demotion exists and is loud, a rollback with
the reason recorded, and the history of an artifact is a straight
line of rungs and reasons that an incident review can read
without an archaeologist.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid, Missing

RUNGS = ("dev", "staging", "canary", "production")


@dataclass
class Ladder:
    positions: dict[str, int] = field(default_factory=dict)
    digests: dict[str, str] = field(default_factory=dict)
    history: list[str] = field(default_factory=list)

    def enter(self, artifact: str, digest: str) -> str:
        if artifact in self.positions:
            raise Invalid(
                f"{artifact} is already on the ladder; artifacts "
                "enter once and move, they do not re-enter"
            )
        self.positions[artifact] = 0
        self.digests[artifact] = digest
        self.history.append(f"{artifact} entered dev ({digest[:8]})")
        return f"{artifact} is on dev"

    def _check(self, artifact: str, digest: str) -> None:
        if artifact not in self.positions:
            raise Missing(f"{artifact} is not on the ladder")
        if self.digests[artifact] != digest:
            raise Invalid(
                f"{artifact} digest mismatch: the ladder holds "
                f"{self.digests[artifact][:8]}, the promotion "
                f"presents {digest[:8]}; someone rebuilt instead "
                "of promoting"
            )

    def promote(self, artifact: str, digest: str) -> str:
        self._check(artifact, digest)
        rung = self.positions[artifact]
        if rung == len(RUNGS) - 1:
            raise Invalid(
                f"{artifact} is already in production; there is "
                "no rung above"
            )
        self.positions[artifact] = rung + 1
        target = RUNGS[rung + 1]
        self.history.append(
            f"{artifact} promoted {RUNGS[rung]} -> {target}"
        )
        return f"{artifact} is on {target}, same bytes"

    def demote(
        self, artifact: str, digest: str, reason: str
    ) -> str:
        self._check(artifact, digest)
        if not reason.strip():
            raise Invalid(
                "a demotion without a reason is an incident "
                "without a report"
            )
        rung = self.positions[artifact]
        if rung == 0:
            raise Invalid(f"{artifact} is already at the bottom")
        self.positions[artifact] = rung - 1
        target = RUNGS[rung - 1]
        self.history.append(
            f"{artifact} demoted {RUNGS[rung]} -> {target}: "
            f"{reason}"
        )
        return f"{artifact} rolled back to {target}: {reason}"

    def where(self, artifact: str) -> str:
        if artifact not in self.positions:
            raise Missing(f"{artifact} is not on the ladder")
        return RUNGS[self.positions[artifact]]

    def story(self, artifact: str) -> str:
        lines = [
            entry
            for entry in self.history
            if entry.startswith(artifact + " ")
        ]
        if not lines:
            raise Missing(f"{artifact} has no history")
        return "\n".join(lines)
