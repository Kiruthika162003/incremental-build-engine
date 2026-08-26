"""The stamp quarantine holds at any tower height, and the leak is loud.

A release built from eight compiled units plus a version stamp:
the cold build runs all nine rules, and every restamp after it
runs exactly one, the assembly, with eight hits and 64 ticks of
compile work untouched, for any number of restamps in a row. Then
the audit commits the classic sin on purpose, wiring the stamp
into one compile step, and the same restamp now runs two rules,
the leaky compile and the assembly, with the quarantine check
failing loudly at rebuilds-equal-one. The measured pair is the
argument for keeping version.stamp out of compile flags: every
compile that reads the stamp joins every future restamp, and the
graph pays that toll forever.
"""

from __future__ import annotations

from forge.actions import Action
from forge.audits.finding import Finding
from forge.stamps import STAMP_PATH, stamped_tower

UNITS = 8


def run() -> Finding:
    project, tree = stamped_tower(units=UNITS)
    project.engine.build("release", tree)
    restamps = []
    for number in range(3):
        report = project.restamp_and_build(tree, f"v1.0.{number}")
        restamps.append(
            (len(report.ran), project.quarantine_holds(report))
        )
    clean_runs = [runs for runs, _ in restamps]
    clean_holds = all(held for _, held in restamps)

    def leaky_rule(view) -> None:
        stamp = view.read_text(STAMP_PATH)
        view.write_text(
            "unit0.o", f"obj({view.read_text('unit0.c')}@{stamp})"
        )

    project.engine.actions["unit0.o"] = Action(
        name="compile unit0.c",
        command="cc",
        reads=("unit0.c", STAMP_PATH),
        writes=("unit0.o",),
        rule=leaky_rule,
    )
    project.restamp_and_build(tree, "v2.0.0")
    leaked = project.restamp_and_build(tree, "v2.0.1")
    numbers = {
        "clean_restamp_rules": max(clean_runs),
        "clean_quarantine_holds": clean_holds,
        "leaked_restamp_rules": len(leaked.ran),
        "leak_detected": not project.quarantine_holds(leaked),
    }
    holds = (
        clean_runs == [1, 1, 1]
        and clean_holds
        and len(leaked.ran) == 2
        and numbers["leak_detected"]
    )
    return Finding(
        audit="stampquarantine",
        claim=(
            "three restamps run one rule each with 64 compile ticks "
            "untouched; one careless stamp read doubles the restamp "
            "and the arithmetic catches it"
        ),
        numbers=numbers,
        holds=holds,
    )
