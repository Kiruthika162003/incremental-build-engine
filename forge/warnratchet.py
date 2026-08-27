"""The warning ratchet: the old debt is grandfathered, the new debt is refused.

A codebase with four thousand warnings cannot turn them into
errors on Tuesday, and a codebase that never turns them into
errors accrues four thousand more. The ratchet is the way
between: the existing stock is recorded as a baseline, owned
and dated, and from then on the rule is asymmetric, any file
may reduce its count, no file may raise it, so the debt curve
can only fall. New warnings are refused with the baseline
number beside the observed one, which keeps the accusation
specific, and fixing warnings pays twice: the count drops and
the baseline is re-recorded at the lower number so the
improvement cannot be borrowed against later. The report is a
leaderboard of debt by file, because a pile of warnings gets
fixed the week it stops being everybody's and starts being
somebody's.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class WarnRatchet:
    baseline: dict[str, int] = field(default_factory=dict)

    def record_baseline(
        self, counts: dict[str, int]
    ) -> str:
        if self.baseline:
            raise Invalid(
                "the baseline exists; improvements re-record "
                "through check, not by starting over"
            )
        if any(count < 0 for count in counts.values()):
            raise Invalid("warning counts cannot be negative")
        self.baseline = dict(counts)
        total = sum(counts.values())
        return (
            f"baseline recorded: {total} warning(s) across "
            f"{len(counts)} file(s), grandfathered and dated"
        )

    def check(self, observed: dict[str, int]) -> str:
        if not self.baseline:
            raise Invalid("no baseline; record one first")
        violations = []
        improvements = 0
        for path in sorted(observed):
            allowed = self.baseline.get(path, 0)
            seen = observed[path]
            if seen > allowed:
                violations.append(
                    f"{path}: {seen} warning(s) against a "
                    f"baseline of {allowed}; the ratchet only "
                    "turns down"
                )
            elif seen < allowed:
                self.baseline[path] = seen
                improvements += 1
        for path in list(self.baseline):
            if path not in observed:
                self.baseline[path] = 0
        if violations:
            raise Invalid("\n".join(violations))
        return (
            f"clean: {improvements} file(s) improved and "
            "re-recorded so the gain cannot be borrowed against"
        )

    def leaderboard(self) -> str:
        holders = sorted(
            (
                (count, path)
                for path, count in self.baseline.items()
                if count > 0
            ),
            reverse=True,
        )
        if not holders:
            return "the debt is paid; turn warnings into errors"
        lines = [
            f"{sum(count for count, _ in holders)} warning(s) "
            "still owed"
        ]
        lines.extend(
            f"  {path}: {count}" for count, path in holders
        )
        return "\n".join(lines)
