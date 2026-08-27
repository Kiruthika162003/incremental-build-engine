from __future__ import annotations

import pytest

from forge.actionbatch import BatchRunner, plan_batches
from forge.actions import Action
from forge.errors import Invalid
from forge.graph import Graph
from forge.workspace import Workspace


def lint_action(source: str) -> Action:
    def rule(view) -> None:
        view.write_text(
            f"{source}.ok", f"lint({view.read_text(source)})"
        )

    return Action(
        name=f"lint {source}",
        command="lint --strict",
        reads=(source,),
        writes=(f"{source}.ok",),
        rule=rule,
    )


def world(count: int = 12) -> tuple[Graph, dict, Workspace]:
    graph = Graph()
    actions = {}
    tree = Workspace()
    names = []
    for number in range(count):
        source = f"file{number:02d}.c"
        graph.declare(source)
        tree.write_text(source, f"int f{number};")
        target = f"lint{number:02d}"
        graph.declare(target, needs=(source,))
        actions[target] = lint_action(source)
        names.append(target)
    graph.declare("all", needs=tuple(names))
    actions["all"] = Action(
        name="all",
        command="collect",
        reads=tuple(f"file{number:02d}.c.ok" for number in range(count)),
        writes=("all.ok",),
        rule=lambda view: view.write_text("all.ok", "done"),
    )
    return graph, actions, tree


class TestPlanning:
    def test_compatible_actions_share_a_batch(self):
        graph, actions, _ = world()
        plan = plan_batches(graph, actions, "all", batch_limit=10)
        sizes = sorted(len(batch) for batch in plan.batches)
        assert sizes == [1, 2, 10]

    def test_different_tools_never_share(self):
        graph, actions, _ = world(count=2)
        plan = plan_batches(graph, actions, "all")
        tools = [
            {actions[name].command.split()[0] for name in batch}
            for batch in plan.batches
        ]
        assert all(len(tool_set) == 1 for tool_set in tools)

    def test_the_floor_arithmetic(self):
        graph, actions, _ = world()
        plan = plan_batches(graph, actions, "all", batch_limit=10)
        assert plan.floors_paid() == 9
        assert plan.floors_avoided() == 30

    def test_a_zero_limit_is_refused(self):
        graph, actions, _ = world(count=2)
        with pytest.raises(Invalid):
            plan_batches(graph, actions, "all", batch_limit=0)


class TestHonestKeys:
    def test_each_member_keeps_its_own_cache_entry(self):
        _, actions, tree = world(count=4)
        runner = BatchRunner()
        first = runner.run_batch(
            ["lint00", "lint01", "lint02", "lint03"], actions, tree
        )
        assert set(first.values()) == {"miss"}
        tree.write_text("file01.c", "int f1; // changed")
        second = runner.run_batch(
            ["lint00", "lint01", "lint02", "lint03"], actions, tree
        )
        assert second["lint01"] == "miss"
        assert second["lint00"] == "hit"
        assert second["lint02"] == "hit"

    def test_an_all_hit_batch_spawns_nothing(self):
        _, actions, tree = world(count=3)
        runner = BatchRunner()
        batch = ["lint00", "lint01", "lint02"]
        runner.run_batch(batch, actions, tree)
        spawns_before = runner.spawns
        runner.run_batch(batch, actions, tree)
        assert runner.spawns == spawns_before

    def test_the_savings_line_reads_both_numbers(self):
        graph, actions, tree = world()
        plan = plan_batches(graph, actions, "all", batch_limit=10)
        runner = BatchRunner()
        for batch in plan.batches:
            runner.run_batch(batch, actions, tree)
        assert runner.savings(plan) == (
            "3 spawns for 13 actions; 30 floor ticks avoided"
        )
