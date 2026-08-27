"""An editing session: unsaved buffers, quiet polls, honest jumps.

Run with: python -m examples.editsession
"""

from __future__ import annotations

from forge.compdb import check_freshness, export
from forge.errors import Stale
from forge.graph import Graph
from forge.loader import load
from forge.overlay import Overlay
from forge.watchmode import Watcher
from forge.workspace import Workspace

PROJECT = """
source = main.c

rule = main.o
command = cc -O2
reads = main.c
writes = main.o
needs = main.c

rule = app
command = ld
reads = main.o
writes = app
needs = main.o
"""


def main() -> int:
    engine = load(PROJECT)
    tree = Workspace()
    tree.write_text("main.c", "int main;")
    watcher = Watcher(engine=engine, goal="app")
    watcher.prime(tree)
    print(f"prime:  {watcher.session()}")

    for _ in range(3):
        watcher.poll(tree)
    tree.write_text("main.c", "int main; // saved edit")
    poll = watcher.poll(tree)
    print(f"save:   {poll.line()}")
    print(f"        {watcher.session()}")

    overlay = Overlay(base=tree)
    overlay.open_buffer("main.c", "int main; // still typing")
    action = engine.actions["main.o"]
    disk_key = action.key(tree)
    buffer_key = action.key(overlay)
    print(
        f"buffer: keys "
        f"{'diverge' if disk_key != buffer_key else 'match'}; "
        f"{overlay.shadow_report()}"
    )

    graph = Graph()
    graph.declare("main.c")
    graph.declare("main.o", needs=("main.c",))
    actions = {"main.o": action}
    database = export(graph, actions)
    try:
        check_freshness(database, graph, actions)
        print("compdb: fresh; every jump lands where the build says")
    except Stale:
        print("compdb: stale")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
