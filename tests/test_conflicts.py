from __future__ import annotations

import pytest

from forge.actions import Action
from forge.conflicts import assert_clean, check_conflicts
from forge.errors import Invalid
from forge.graph import Graph


def action(name: str, reads: tuple, writes: tuple) -> Action:
    return Action(
        name=name,
        command="tool",
        reads=reads,
        writes=writes,
        rule=lambda _tree: None,
    )


def clean_world() -> tuple[Graph, dict]:
    graph = Graph()
    graph.declare("gen")
    graph.declare("consumer", needs=("gen",))
    actions = {
        "gen": action("gen", (), ("shared.h",)),
        "consumer": action("consumer", ("shared.h",), ("out.o",)),
    }
    return graph, actions


class TestDoubleWrites:
    def test_a_clean_graph_passes(self):
        graph, actions = clean_world()
        report = check_conflicts(graph, actions)
        assert report.clean()
        assert report.page().startswith("no conflicts")

    def test_two_writers_are_both_named(self):
        graph, actions = clean_world()
        graph.declare("rival")
        actions["rival"] = action("rival", (), ("shared.h",))
        report = check_conflicts(graph, actions)
        assert len(report.double_writes) == 1
        assert "written by both gen and rival" in report.double_writes[0]

    def test_assert_clean_raises_with_the_page(self):
        graph, actions = clean_world()
        graph.declare("rival")
        actions["rival"] = action("rival", (), ("shared.h",))
        with pytest.raises(Invalid, match="scheduler's mood"):
            assert_clean(graph, actions)


class TestUndeclaredRaces:
    def test_a_read_without_an_edge_is_a_race(self):
        graph = Graph()
        graph.declare("gen")
        graph.declare("racer")
        actions = {
            "gen": action("gen", (), ("shared.h",)),
            "racer": action("racer", ("shared.h",), ("out.o",)),
        }
        report = check_conflicts(graph, actions)
        assert len(report.undeclared_races) == 1
        assert "no edge between them" in report.undeclared_races[0]

    def test_a_transitive_edge_settles_the_race(self):
        graph = Graph()
        graph.declare("gen")
        graph.declare("middle", needs=("gen",))
        graph.declare("far", needs=("middle",))
        actions = {
            "gen": action("gen", (), ("shared.h",)),
            "middle": action("middle", ("shared.h",), ("mid.o",)),
            "far": action("far", ("shared.h",), ("far.o",)),
        }
        assert check_conflicts(graph, actions).clean()

    def test_reading_your_own_output_is_not_a_race(self):
        graph = Graph()
        graph.declare("gen")
        graph.declare("user", needs=("gen",))
        actions = {
            "gen": action("gen", (), ("shared.h",)),
            "user": action("user", ("shared.h",), ("out.o",)),
        }
        assert check_conflicts(graph, actions).clean()

    def test_an_action_without_a_target_is_refused(self):
        graph = Graph()
        actions = {"orphan": action("orphan", (), ("x",))}
        with pytest.raises(Invalid, match="no graph target"):
            check_conflicts(graph, actions)
