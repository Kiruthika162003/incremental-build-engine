"""The ship gate: go or no-go, with every no wearing a name.

Release day collects verdicts from organs that spent the week
forming them: the audits page must read zero broken, the error
budget must not be frozen, the clean room's last night must
have renewed trust, the dual-read era must not be holding on
an unexplained disagreement, and the revert tracker must show
no open dispute on the release path. The gate asks each organ
in turn, and its one design rule is that a no is a sentence,
not a light: every blocker arrives with the organ that raised
it and the line it raised, so the release meeting starts at
the fix instead of at the diagnosis. The go verdict is
deliberately underwhelming, one line, all checks named, since
a ship day that feels dramatic is a ship day where the drama
arrived late, and the whole platform upstream of this page
exists to make the page boring.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class ShipGate:
    checks: dict[str, tuple[bool, str]] = field(
        default_factory=dict
    )

    def report(
        self, organ: str, clear: bool, line: str
    ) -> None:
        if organ in self.checks:
            raise Invalid(
                f"{organ} already reported; verdicts do not "
                "get second drafts on ship day"
            )
        if not line.strip():
            raise Invalid(
                f"{organ}: a verdict without its line is a "
                "light, and the gate does not read lights"
            )
        self.checks[organ] = (clear, line)

    def decide(self) -> str:
        if len(self.checks) < 3:
            raise Invalid(
                f"{len(self.checks)} organ(s) reported; a gate "
                "that asks almost nobody is a formality"
            )
        blockers = [
            f"{organ}: {line}"
            for organ, (clear, line) in sorted(
                self.checks.items()
            )
            if not clear
        ]
        if blockers:
            lines = [
                f"NO-GO: {len(blockers)} blocker(s), each "
                "wearing a name"
            ]
            lines.extend(f"  {entry}" for entry in blockers)
            lines.append(
                "the meeting starts at the fix, not at the "
                "diagnosis"
            )
            return "\n".join(lines)
        named = ", ".join(sorted(self.checks))
        return (
            f"GO ({named}); deliberately underwhelming, "
            "because the platform upstream of this page "
            "exists to make it boring"
        )
