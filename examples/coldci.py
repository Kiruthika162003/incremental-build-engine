"""A cold CI morning: lazy fetches, batched lints, a flaky rule caught.

Run with: python -m examples.coldci
"""

from __future__ import annotations

from forge.actionbatch import BatchRunner, plan_batches
from forge.actions import Action
from forge.content import ContentStore
from forge.flaky import Certifier
from forge.graph import Graph
from forge.lazyoutputs import LazyTree
from forge.workspace import Workspace


def lint_fleet() -> tuple[Graph, dict, Workspace]:
    graph = Graph()
    actions = {}
    tree = Workspace()
    names = []
    for number in range(8):
        source = f"src/f{number}.c"
        target = f"lint{number}"
        graph.declare(source)
        tree.write_text(source, f"int f{number};")

        def rule(view, source=source, target=target) -> None:
            view.write_text(
                f"{target}.ok", f"lint({view.read_text(source)})"
            )

        graph.declare(target, needs=(source,))
        actions[target] = Action(
            name=target,
            command="lint --strict",
            reads=(source,),
            writes=(f"{target}.ok",),
            rule=rule,
        )
        names.append(target)
    graph.declare("all", needs=tuple(names))
    actions["all"] = Action(
        name="all",
        command="collect",
        reads=tuple(f"lint{number}.ok" for number in range(8)),
        writes=("all.ok",),
        rule=lambda view: view.write_text("all.ok", "green"),
    )
    return graph, actions, tree


def stamper() -> Action:
    ticks = [0]

    def rule(view) -> None:
        ticks[0] += 1
        view.write_text("stamp.out", f"built at tick {ticks[0]}")

    return Action(
        name="stamper",
        command="cc -DNOW",
        reads=(),
        writes=("stamp.out",),
        rule=rule,
    )


def main() -> int:
    graph, actions, tree = lint_fleet()
    plan = plan_batches(graph, actions, "all", batch_limit=4)
    runner = BatchRunner()
    for batch in plan.batches:
        runner.run_batch(batch, actions, tree)
    print(f"lints:   {runner.savings(plan)}")

    certifier = Certifier()
    probe_tree = Workspace()
    verdict = certifier.certify(stamper(), probe_tree)
    print(f"probe:   {verdict.line()}")

    lazy = LazyTree(store=ContentStore())
    for number in range(8):
        lazy.refer(f"obj/lint{number}.ok", b"ok" * 50)
    lazy.refer("report.html", b"<html>green</html>")
    lazy.open("report.html")
    print(f"fetch:   {lazy.ledger()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
