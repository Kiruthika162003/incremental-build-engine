from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.graph import Graph
from forge.impliededges import EdgeReducer


def diamond_with_shortcut() -> EdgeReducer:
    graph = Graph()
    graph.declare("core")
    graph.declare("util", needs=("core",))
    graph.declare("app", needs=("util", "core"))
    return EdgeReducer(graph=graph)


class TestDetection:
    def test_the_shortcut_edge_is_named_with_its_witness(self):
        redundant = diamond_with_shortcut().redundant_edges()
        assert redundant == [
            ("app", "core", "app -> util -> core")
        ]

    def test_a_chain_has_no_implied_edges(self):
        graph = Graph()
        graph.declare("a")
        graph.declare("b", needs=("a",))
        graph.declare("c", needs=("b",))
        assert EdgeReducer(graph=graph).redundant_edges() == []

    def test_parallel_branches_are_not_confused(self):
        graph = Graph()
        graph.declare("base")
        graph.declare("left", needs=("base",))
        graph.declare("right", needs=("base",))
        graph.declare("top", needs=("left", "right"))
        assert EdgeReducer(graph=graph).redundant_edges() == []


class TestTheReport:
    def test_the_report_recommends_and_defers(self):
        report = diamond_with_shortcut().report()
        assert report.startswith(
            "1 of 3 edge(s) are already implied"
        )
        assert (
            "app -> core is restated by app -> util -> core"
        ) in report
        assert "only a person knows if it was a contract" in report

    def test_a_lean_graph_is_praised(self):
        graph = Graph()
        graph.declare("a")
        graph.declare("b", needs=("a",))
        assert EdgeReducer(graph=graph).report().startswith(
            "1 edge(s), none implied"
        )

    def test_an_empty_graph_is_refused(self):
        with pytest.raises(Invalid):
            EdgeReducer(graph=Graph()).report()
