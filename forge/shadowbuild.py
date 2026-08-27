"""Shadow builds: the migration argument is an agreement percentage.

Nobody migrates build systems on faith; they migrate on a number.
The shadow rig runs the old system and the new system over the
same targets and compares outputs digest by digest, and the
number that ends the meeting is agreement: 96 percent means
finish the last four, 60 percent means the new system is still
an experiment. Disagreements are triaged, not just counted,
because they are not one problem: outputs that differ are
miscompiles to fix, outputs only the old system produces are
migration gaps to close, and outputs only the new system
produces are usually stamps and manifests to allowlist. The
ratchet makes the migration monotonic: once a target agrees, a
later disagreement is a regression named loudly, since a
migration that can silently lose ground never finishes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class ShadowRun:
    old_outputs: dict[str, str]
    new_outputs: dict[str, str]

    def agreements(self) -> list[str]:
        return sorted(
            path
            for path, digest in self.old_outputs.items()
            if self.new_outputs.get(path) == digest
        )

    def miscompiles(self) -> list[str]:
        return sorted(
            path
            for path, digest in self.old_outputs.items()
            if path in self.new_outputs
            and self.new_outputs[path] != digest
        )

    def gaps(self) -> list[str]:
        return sorted(
            set(self.old_outputs) - set(self.new_outputs)
        )

    def extras(self) -> list[str]:
        return sorted(
            set(self.new_outputs) - set(self.old_outputs)
        )

    def agreement_percent(self) -> int:
        if not self.old_outputs:
            raise Invalid(
                "the old system produced nothing; there is no "
                "baseline to shadow"
            )
        return round(
            100 * len(self.agreements()) / len(self.old_outputs)
        )

    def triage(self) -> str:
        percent = self.agreement_percent()
        lines = [
            f"agreement {percent}% "
            f"({len(self.agreements())} of "
            f"{len(self.old_outputs)} outputs)"
        ]
        if self.miscompiles():
            lines.append(
                f"  differ (fix these first): "
                f"{', '.join(self.miscompiles())}"
            )
        if self.gaps():
            lines.append(
                f"  only the old system builds: "
                f"{', '.join(self.gaps())}"
            )
        if self.extras():
            lines.append(
                f"  only the new system builds (usually stamps "
                f"to allowlist): {', '.join(self.extras())}"
            )
        if percent == 100 and not self.extras():
            lines.append("  the shadow is the system; cut over")
        return "\n".join(lines)


@dataclass
class MigrationRatchet:
    agreed: set[str] = field(default_factory=set)
    regressions: list[str] = field(default_factory=list)

    def advance(self, run: ShadowRun) -> str:
        now_agreeing = set(run.agreements())
        lost = sorted(self.agreed - now_agreeing)
        gained = sorted(now_agreeing - self.agreed)
        for path in lost:
            self.regressions.append(path)
        self.agreed |= now_agreeing
        if lost:
            return (
                f"REGRESSION: {', '.join(lost)} agreed before "
                "and disagree now; a migration that can silently "
                "lose ground never finishes"
            )
        if gained:
            return (
                f"ratchet advances: {len(gained)} new "
                f"agreement(s) ({', '.join(gained)}), "
                f"{len(self.agreed)} held total"
            )
        return f"holding at {len(self.agreed)} agreement(s)"
