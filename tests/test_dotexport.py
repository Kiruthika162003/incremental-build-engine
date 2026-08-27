from __future__ import annotations

import pytest

from forge.dotexport import to_dot
from forge.errors import Missing
from forge.graph import Graph


def graph() -> Graph:
    built = Graph()
    built.declare("main.c")
    built.declare("main.o", needs=("main.c",))
    built.declare("app", needs=("main.o",))
    built.declare("unrelated")
    return built


class TestTheDrawing:
    def test_sources_are_boxes_and_targets_ellipses(self):
        page = to_dot(graph(), actions={"main.o", "app"})
        assert '"main.c" [shape=box];' in page
        assert '"main.o" [shape=ellipse];' in page

    def test_every_edge_is_drawn(self):
        page = to_dot(graph())
        assert '"app" -> "main.o";' in page
        assert '"main.o" -> "main.c";' in page

    def test_a_goal_scopes_the_picture(self):
        page = to_dot(graph(), goal="app")
        assert "unrelated" not in page

    def test_the_export_is_deterministic(self):
        assert to_dot(graph()) == to_dot(graph())


class TestHighlights:
    def test_the_somepath_answer_becomes_a_red_line(self):
        page = to_dot(
            graph(),
            goal="app",
            highlight=["app", "main.o", "main.c"],
        )
        assert '"app" [shape=box, penwidth=3];' in page
        assert '"app" -> "main.o" [penwidth=3, color=red];' in page

    def test_unhighlighted_edges_stay_plain(self):
        page = to_dot(graph(), highlight=["app", "main.o"])
        assert '"main.o" -> "main.c";' in page

    def test_a_ghost_goal_is_refused_not_drawn_empty(self):
        with pytest.raises(Missing, match="not in the room"):
            to_dot(graph(), goal="ghost")
