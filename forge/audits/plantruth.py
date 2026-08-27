"""The plan against the engine: prediction walks the graph, digests walk truer.

The planner prices a comment edit to core.c at two targets, the
recompile and the relink, because prediction can only walk
edges. The engine then runs the recompile, the comment strips
out, the object comes back byte-identical, and the relink the
plan billed becomes a cache hit through early cutoff. Both
sides are correct at their own layer, which is the audit's
finding: a build plan is an upper bound, not a forecast, high
by exactly the cutoffs that only execution can discover, and a
team reading plans should read them the way they read quotes
from a contractor who has not yet opened the wall.
"""

from __future__ import annotations

from forge.actions import Action
from forge.audits.finding import Finding
from forge.buildplan import BuildPlanner
from forge.engine import Engine
from forge.workspace import Workspace


def _engine() -> Engine:
    engine = Engine()
    engine.source("core.c")

    def compile_rule(tree) -> None:
        code = tree.read_text("core.c").split("//")[0].strip()
        tree.write_text("core.o", f"obj({code})")

    def link_rule(tree) -> None:
        tree.write_text(
            "app", f"bin[{tree.read_text('core.o')}]"
        )

    engine.rule(
        "core.o",
        Action(
            name="core.o",
            command="cc -strip-comments",
            reads=("core.c",),
            writes=("core.o",),
            rule=compile_rule,
        ),
        needs=("core.c",),
    )
    engine.rule(
        "app",
        Action(
            name="app",
            command="ld",
            reads=("core.o",),
            writes=("app",),
            rule=link_rule,
        ),
        needs=("core.o",),
    )
    return engine


def run() -> Finding:
    engine = _engine()
    tree = Workspace()
    tree.write_text("core.c", "int main;")
    cold = engine.build("app", tree)
    planner = BuildPlanner(
        graph=engine.graph,
        sources_of={"core.o": ("core.c",), "app": ()},
        cost_of={"core.o": 30, "app": 20},
    )
    plan = planner.plan(("core.c",))
    predicted_runs = int(plan.split(" target(s) run")[0])
    tree.write_text("core.c", "int main; // comment only")
    warm = engine.build("app", tree)
    cutoffs = engine.cutoff_count(cold, warm)
    numbers = {
        "predicted_runs": predicted_runs,
        "predicted_ticks": 50,
        "actual_ran": len(warm.ran),
        "actual_hits": len(warm.hits),
        "cutoffs": cutoffs,
        "overpromise": predicted_runs - len(warm.ran),
    }
    holds = (
        numbers["predicted_runs"] == 2
        and numbers["actual_ran"] == 1
        and numbers["actual_hits"] == 1
        and numbers["cutoffs"] == 1
        and numbers["overpromise"] == 1
    )
    return Finding(
        audit="plantruth",
        claim=(
            "the plan bills two targets and the engine pays "
            "one: prediction walks edges while execution walks "
            "digests, so a plan is an upper bound high by "
            "exactly the cutoffs only running can discover"
        ),
        numbers=numbers,
        holds=holds,
    )
