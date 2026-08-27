"""Golden files: the snapshot is a promise, and blessing is a ceremony.

A golden test fails for two reasons that deserve opposite
responses: the code broke, or the truth legitimately moved. The
manager keeps the ceremony honest by making the second path
explicit: a mismatch is reported with a compact diff summary,
and updating the golden requires a bless call carrying a reason,
which is recorded next to the new digest. The dangerous habit is
bulk blessing, running the update flag over a red suite until it
is green, so the ledger counts blessings per session and flags
the session that blessed more than it read, because a hundred
goldens updated with one reason between them is not a review,
it is a surrender with paperwork.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.content import digest_text
from forge.errors import Invalid, Missing

BULK_SUSPICION = 3


@dataclass
class GoldenStore:
    goldens: dict[str, str] = field(default_factory=dict)
    reasons: dict[str, str] = field(default_factory=dict)
    blessed_this_session: list[str] = field(default_factory=list)
    checks_this_session: int = 0

    def record(self, name: str, content: str) -> None:
        if name in self.goldens:
            raise Invalid(
                f"{name} exists; changing it is a bless, not a "
                "record"
            )
        self.goldens[name] = content

    def check(self, name: str, actual: str) -> str:
        if name not in self.goldens:
            raise Missing(
                f"{name} has no golden; record one deliberately"
            )
        self.checks_this_session += 1
        expected = self.goldens[name]
        if actual == expected:
            return f"{name}: matches"
        expected_lines = expected.splitlines()
        actual_lines = actual.splitlines()
        first_diff = next(
            (
                index + 1
                for index, (a, b) in enumerate(
                    zip(expected_lines, actual_lines, strict=False)
                )
                if a != b
            ),
            min(len(expected_lines), len(actual_lines)) + 1,
        )
        return (
            f"{name}: MISMATCH at line {first_diff} "
            f"(golden {len(expected_lines)} line(s), actual "
            f"{len(actual_lines)}); bless with a reason or fix "
            "the code"
        )

    def bless(self, name: str, actual: str, reason: str) -> str:
        if name not in self.goldens:
            raise Missing(f"{name} has no golden to bless")
        if not reason.strip():
            raise Invalid(
                "a blessing without a reason is a surrender "
                "with paperwork"
            )
        if self.goldens[name] == actual:
            raise Invalid(
                f"{name} already matches; blessing it would "
                "record a reason for nothing"
            )
        self.goldens[name] = actual
        self.reasons[name] = reason
        self.blessed_this_session.append(name)
        return (
            f"{name} blessed ({digest_text(actual)[:8]}): {reason}"
        )

    def session_verdict(self) -> str:
        blessed = len(self.blessed_this_session)
        if blessed == 0:
            return (
                f"{self.checks_this_session} check(s), no "
                "blessings; the goldens held"
            )
        line = (
            f"{self.checks_this_session} check(s), {blessed} "
            f"blessing(s)"
        )
        if (
            blessed >= BULK_SUSPICION
            and blessed > self.checks_this_session
        ):
            line += (
                ": more blessed than read; that is not a "
                "review, it is a surrender with paperwork"
            )
        return line
