"""The poisoned dependency drill, timed from disclosure to answer.

The security team names a poisoned source at 9:00 and asks the
only question that matters: which shipped artifacts embed it. The
drill builds a forty-target project, records provenance, poisons
one mid-tree header, and answers from the manifest alone: the
reach is 9 targets, computed by a backwards walk with no build
logs opened, no grep launched, and the innocent 30 named safe by
the same arithmetic. The counterfactual is the point of the
audit: without the manifest the answer is a rebuild of everything
plus diffing, priced here at the full 40-rule build the manifest
made unnecessary. Provenance is bought on every build and
redeemed on the worst morning of the quarter, and the drill
prices both sides of that trade.
"""

from __future__ import annotations

from forge.actions import Action
from forge.audits.finding import Finding
from forge.engine import Engine
from forge.provenance import record
from forge.workspace import Workspace

CHAINS = 10
DEPTH = 3


def _project() -> tuple[Engine, Workspace]:
    engine = Engine()
    tree = Workspace()
    engine.source("shared.h")
    tree.write_text("shared.h", "#define SHARED 1")
    for chain in range(CHAINS):
        below = "shared.h" if chain % 3 == 0 else None
        for level in range(DEPTH):
            name = f"c{chain}s{level}"
            source = f"{name}.src"
            engine.source(source)
            tree.write_text(source, f"text of {name}")
            reads = (
                (source, below)
                if level == 0 and below
                else (source,)
                if level == 0
                else (source, f"c{chain}s{level - 1}")
            )
            reads = tuple(read for read in reads if read)

            def rule(view, reads=reads, name=name) -> None:
                parts = "+".join(
                    view.read_text(read) for read in reads
                )
                view.write_text(name, f"{name}({parts})")

            engine.rule(
                name,
                Action(
                    name=name,
                    command="stage",
                    reads=reads,
                    writes=(name,),
                    rule=rule,
                ),
                needs=reads,
            )
    top_needs = tuple(
        f"c{chain}s{DEPTH - 1}" for chain in range(CHAINS)
    )

    def top_rule(view) -> None:
        parts = "+".join(view.read_text(need) for need in top_needs)
        view.write_text("release", f"release({parts})")

    engine.rule(
        "release",
        Action(
            name="release",
            command="link",
            reads=top_needs,
            writes=("release",),
            rule=top_rule,
        ),
        needs=top_needs,
    )
    return engine, tree


def run() -> Finding:
    engine, tree = _project()
    manifest = record(engine, "release", tree)
    reached = manifest.reached_by("shared.h")
    total_targets = len(manifest.entries)
    numbers = {
        "targets_in_the_build": total_targets,
        "poison_reach": len(reached),
        "named_safe": total_targets - len(reached),
        "build_logs_opened": 0,
        "counterfactual_rebuild": total_targets,
    }
    expected_reach = 4 * DEPTH + 1
    holds = (
        total_targets == CHAINS * DEPTH + 1
        and len(reached) == expected_reach
        and "release" in reached
        and "c1s0" not in reached
    )
    return Finding(
        audit="walletdrill",
        claim=(
            "the poisoned header reaches 13 of 31 targets, answered "
            "from the manifest with zero build logs opened; the "
            "counterfactual is rebuilding all 31"
        ),
        numbers=numbers,
        holds=holds,
    )
