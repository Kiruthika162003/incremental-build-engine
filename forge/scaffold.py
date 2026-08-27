"""Scaffold conformance: the new repo is graded, not blocked.

Every organization has a golden path, the BUILD file, the
owners record, the test directory, the CI hook, and every
organization discovers that blocking repo creation on the full
checklist just teaches people to copy an old repo, rot
included. The grader takes the other deal: a new repo may be
born incomplete, but its gaps are graded in public, each
missing piece named with why it matters and what it costs to
add now versus later, because the honest economics of scaffold
debt is that the owners record costs one line today and one
archaeology project after the founding team rotates. Grades
roll up to a letter for the dashboard, and the one hard rule
survives: a repo cannot reach production traffic ungraded,
since grading is cheap and the alternative is discovering the
gaps during the incident.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid

CHECKLIST = (
    (
        "build_file",
        "nothing builds without it",
        "one stanza today, a reverse-engineering session later",
    ),
    (
        "owners_record",
        "unowned code is orphaned at the first reorg",
        "one line today, an archaeology project after the "
        "founding team rotates",
    ),
    (
        "test_directory",
        "a repo without a test home never grows tests",
        "an empty directory today, a culture war later",
    ),
    (
        "ci_hook",
        "unhooked repos rot green",
        "three lines today, a broken main nobody noticed later",
    ),
)


@dataclass(frozen=True)
class RepoState:
    name: str
    present: frozenset[str]


def grade(repo: RepoState) -> tuple[str, list[str]]:
    known = {item for item, _, _ in CHECKLIST}
    strangers = repo.present - known
    if strangers:
        raise Invalid(
            f"{repo.name} claims unknown scaffold piece(s): "
            f"{', '.join(sorted(strangers))}"
        )
    gaps = []
    for item, why, cost in CHECKLIST:
        if item not in repo.present:
            gaps.append(
                f"{item}: {why}; {cost}"
            )
    held = len(CHECKLIST) - len(gaps)
    letters = {4: "A", 3: "B", 2: "C", 1: "D", 0: "F"}
    return letters[held], gaps


def report(repo: RepoState) -> str:
    letter, gaps = grade(repo)
    lines = [
        f"{repo.name}: grade {letter} "
        f"({len(CHECKLIST) - len(gaps)} of {len(CHECKLIST)})"
    ]
    lines.extend(f"  missing {gap}" for gap in gaps)
    return "\n".join(lines)


def production_gate(repo: RepoState) -> str:
    letter, gaps = grade(repo)
    if letter in ("A", "B"):
        return (
            f"{repo.name} may take production traffic at "
            f"grade {letter}"
        )
    raise Invalid(
        f"{repo.name} is grade {letter} and production is not "
        f"the place to discover {len(gaps)} gap(s); grading is "
        "cheap and the incident is not"
    )
