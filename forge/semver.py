"""Semver advice from interface diffs: the version number is a computation.

Teams argue about version numbers because they argue from memory:
somebody thinks the renamed helper was public, somebody forgot
the new optional argument. The advisor compares two interface
snapshots and applies the rules mechanically: a removed or
changed public symbol is breaking and demands a major bump, a new
public symbol is a feature and demands at least minor, and a
release that changes nothing public is a patch no matter how
violent the internals were. The advice names the symbols that
forced the verdict, because "major, due to remove(parse_v1)" ends
the meeting that "probably major?" starts. Downgrading the
required bump is refused outright; shipping a breaking change as
a minor is not a policy choice, it is a broken promise with a
changelog.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid

MAJOR = "major"
MINOR = "minor"
PATCH = "patch"
RANKS = {PATCH: 0, MINOR: 1, MAJOR: 2}


@dataclass(frozen=True)
class Advice:
    bump: str
    reasons: tuple[str, ...]

    def line(self) -> str:
        if not self.reasons:
            return (
                f"{self.bump}: nothing public moved; internals "
                "do not version"
            )
        return f"{self.bump}, due to {', '.join(self.reasons)}"


def advise(
    before: dict[str, str], after: dict[str, str]
) -> Advice:
    reasons = []
    bump = PATCH
    for name in sorted(before):
        if name not in after:
            reasons.append(f"remove({name})")
            bump = MAJOR
        elif before[name] != after[name]:
            reasons.append(f"change({name})")
            bump = MAJOR
    for name in sorted(after):
        if name not in before:
            reasons.append(f"add({name})")
            if bump != MAJOR:
                bump = MINOR
    return Advice(bump=bump, reasons=tuple(reasons))


def next_version(
    current: tuple[int, int, int],
    before: dict[str, str],
    after: dict[str, str],
    proposed_bump: str | None = None,
) -> tuple[int, int, int]:
    advice = advise(before, after)
    chosen = advice.bump
    if proposed_bump is not None:
        if proposed_bump not in RANKS:
            raise Invalid(f"unknown bump kind {proposed_bump}")
        if RANKS[proposed_bump] < RANKS[advice.bump]:
            raise Invalid(
                f"the diff demands a {advice.bump} bump "
                f"({', '.join(advice.reasons)}); shipping it as "
                f"{proposed_bump} is a broken promise with a "
                "changelog"
            )
        chosen = proposed_bump
    major, minor, patch = current
    if chosen == MAJOR:
        return (major + 1, 0, 0)
    if chosen == MINOR:
        return (major, minor + 1, 0)
    return (major, minor, patch + 1)


def release_note(
    current: tuple[int, int, int],
    before: dict[str, str],
    after: dict[str, str],
) -> str:
    advice = advise(before, after)
    version = next_version(current, before, after)
    dotted = ".".join(str(part) for part in version)
    return f"{dotted} ({advice.line()})"
