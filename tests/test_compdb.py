from __future__ import annotations

import pytest

from forge.actions import Action
from forge.compdb import check_freshness, export
from forge.errors import Stale
from forge.graph import Graph


def action(name: str, command: str, reads: tuple) -> Action:
    return Action(
        name=name,
        command=command,
        reads=reads,
        writes=(f"{name}.out",),
        rule=lambda _tree: None,
    )


def project() -> tuple[Graph, dict]:
    graph = Graph()
    graph.declare("main.c")
    graph.declare("lib.c")
    graph.declare("main.o", needs=("main.c",))
    graph.declare("lib.o", needs=("lib.c",))
    graph.declare("app", needs=("main.o", "lib.o"))
    actions = {
        "main.o": action("main.o", "cc -O2", ("main.c",)),
        "lib.o": action("lib.o", "cc -O2 -Wall", ("lib.c",)),
        "app": action("app", "ld", ("main.o", "lib.o")),
    }
    return graph, actions


class TestExport:
    def test_compiles_are_exported_with_exact_commands(self):
        graph, actions = project()
        database = export(graph, actions)
        assert '"file": "lib.c"' in database
        assert '"command": "cc -O2 -Wall lib.c"' in database

    def test_the_linker_is_not_a_compile(self):
        graph, actions = project()
        assert '"command": "ld' not in export(graph, actions)

    def test_the_export_is_stable(self):
        graph, actions = project()
        assert export(graph, actions) == export(graph, actions)

    def test_the_directory_travels(self):
        graph, actions = project()
        database = export(graph, actions, directory="/repo")
        assert '"directory": "/repo"' in database


class TestFreshness:
    def test_a_fresh_database_passes(self):
        graph, actions = project()
        database = export(graph, actions)
        check_freshness(database, graph, actions)

    def test_a_flag_change_stales_the_database(self):
        graph, actions = project()
        database = export(graph, actions)
        actions["main.o"] = action("main.o", "cc -O3", ("main.c",))
        with pytest.raises(Stale, match="regenerate it"):
            check_freshness(database, graph, actions)

    def test_a_new_source_stales_the_database_too(self):
        graph, actions = project()
        database = export(graph, actions)
        graph.declare("extra.c")
        graph.declare("extra.o", needs=("extra.c",))
        actions["extra.o"] = action("extra.o", "cc -O2", ("extra.c",))
        with pytest.raises(Stale):
            check_freshness(database, graph, actions)
