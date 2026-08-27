"""Batching pays for the lint fleet exactly once per wave per tool.

Twenty-four lints and a collector, batch limit eight: the plan
packs the lint wave into three batches plus the collector's own,
paying four spawn floors where the unbatched world pays
twenty-five, a saving of 63 floor ticks at three per spawn. The
second run is the audit's sharper half: everything hits, no batch
spawns at all, and the savings line reads zero spawns for
twenty-five actions, which pins the interaction between the two
optimisations: batching amortises the floor on cold builds, the
cache deletes it on warm ones, and neither steals the other's
credit because the per-action keys were never merged.
"""

from __future__ import annotations

from forge.actionbatch import BatchRunner, plan_batches
from forge.actions import Action
from forge.audits.finding import Finding
from forge.graph import Graph
from forge.workspace import Workspace

LINTS = 24
LIMIT = 8


def _fleet() -> tuple[Graph, dict, Workspace]:
    graph = Graph()
    actions = {}
    tree = Workspace()
    names = []
    for number in range(LINTS):
        source = f"f{number:02d}.c"
        target = f"lint{number:02d}"
        graph.declare(source)
        tree.write_text(source, f"int f{number};")

        def rule(view, source=source, target=target) -> None:
            view.write_text(
                f"{target}.ok", f"ok({view.read_text(source)})"
            )

        graph.declare(target, needs=(source,))
        actions[target] = Action(
            name=target,
            command="lint",
            reads=(source,),
            writes=(f"{target}.ok",),
            rule=rule,
        )
        names.append(target)
    graph.declare("all", needs=tuple(names))
    actions["all"] = Action(
        name="all",
        command="collect",
        reads=tuple(f"lint{number:02d}.ok" for number in range(LINTS)),
        writes=("all.ok",),
        rule=lambda view: view.write_text("all.ok", "done"),
    )
    return graph, actions, tree


def run() -> Finding:
    graph, actions, tree = _fleet()
    plan = plan_batches(graph, actions, "all", batch_limit=LIMIT)
    runner = BatchRunner()
    for batch in plan.batches:
        runner.run_batch(batch, actions, tree)
    cold_spawns = runner.spawns
    for batch in plan.batches:
        runner.run_batch(batch, actions, tree)
    warm_spawns = runner.spawns - cold_spawns
    numbers = {
        "batches": len(plan.batches),
        "cold_spawns": cold_spawns,
        "unbatched_world_spawns": LINTS + 1,
        "floor_ticks_avoided": plan.floors_avoided(),
        "warm_spawns": warm_spawns,
    }
    holds = (
        len(plan.batches) == 4
        and cold_spawns == 4
        and plan.floors_avoided() == 63
        and warm_spawns == 0
    )
    return Finding(
        audit="batcheconomy",
        claim=(
            "four spawns where the unbatched world pays twenty-five, "
            "63 floor ticks avoided; the warm run spawns zero because "
            "the per-action keys were never merged"
        ),
        numbers=numbers,
        holds=holds,
    )
