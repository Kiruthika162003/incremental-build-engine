from __future__ import annotations

import pytest

from forge.errors import Cycle, Invalid, Missing
from forge.graph import Graph, Target


def diamond() -> Graph:
    graph = Graph()
    graph.declare("base")
    graph.declare("left", needs=("base",))
    graph.declare("right", needs=("base",))
    graph.declare("app", needs=("left", "right"))
    return graph


class TestDeclaration:
    def test_targets_need_names(self):
        with pytest.raises(Invalid):
            Target(name="")

    def test_self_dependency_is_refused_at_the_door(self):
        with pytest.raises(Invalid):
            Target(name="a", needs=("a",))

    def test_double_declaration_is_refused(self):
        graph = diamond()
        with pytest.raises(Invalid):
            graph.declare("base")

    def test_a_cycle_is_named_with_its_full_loop(self):
        graph = Graph()
        graph.declare("a", needs=("b",))
        graph.declare("b", needs=("c",))
        with pytest.raises(Cycle, match="c -> a -> b -> c"):
            graph.declare("c", needs=("a",))

    def test_a_refused_cycle_leaves_the_graph_clean(self):
        graph = Graph()
        graph.declare("a", needs=("b",))
        graph.declare("b", needs=("c",))
        with pytest.raises(Cycle):
            graph.declare("c", needs=("a",))
        assert "c" not in graph.targets

    def test_forward_references_are_legal_and_reported(self):
        graph = Graph()
        graph.declare("app", needs=("lib",))
        assert graph.missing_needs() == {"app": ["lib"]}
        graph.declare("lib")
        assert graph.missing_needs() == {}


class TestOrdering:
    def test_dependencies_come_first_and_ties_break_by_name(self):
        assert diamond().build_order("app") == [
            "base",
            "left",
            "right",
            "app",
        ]

    def test_the_order_covers_only_what_the_goal_needs(self):
        graph = diamond()
        graph.declare("unrelated")
        assert "unrelated" not in graph.build_order("app")

    def test_an_unknown_goal_is_refused(self):
        with pytest.raises(Missing):
            diamond().build_order("ghost")


class TestImpact:
    def test_downstream_walks_the_whole_blast(self):
        assert diamond().downstream_of("base") == ["app", "left", "right"]

    def test_leaves_have_no_downstream(self):
        assert diamond().downstream_of("app") == []


class TestWaves:
    def test_waves_group_what_can_run_together(self):
        assert diamond().waves("app") == [
            ["base"],
            ["left", "right"],
            ["app"],
        ]

    def test_width_is_the_widest_wave(self):
        assert diamond().width("app") == 2

    def test_a_chain_has_width_one(self):
        graph = Graph()
        graph.declare("a")
        graph.declare("b", needs=("a",))
        graph.declare("c", needs=("b",))
        assert graph.width("c") == 1
        assert graph.waves("c") == [["a"], ["b"], ["c"]]
