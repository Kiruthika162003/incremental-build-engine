from __future__ import annotations

from forge.graph import Graph
from forge.graphdiff import cache_impact, diff, review_page


def original() -> Graph:
    graph = Graph()
    graph.declare("base")
    graph.declare("util", needs=("base",))
    graph.declare("app", needs=("util",))
    graph.declare("installer", needs=("app",))
    return graph


def rewired() -> Graph:
    graph = Graph()
    graph.declare("base")
    graph.declare("netlib")
    graph.declare("util", needs=("base", "netlib"))
    graph.declare("app", needs=("util",))
    graph.declare("installer", needs=("app",))
    return graph


class TestDiff:
    def test_identical_graphs_are_quiet(self):
        delta = diff(original(), original())
        assert delta.quiet()
        assert review_page(original(), original()).startswith(
            "no structural change"
        )

    def test_additions_and_edges_are_named(self):
        delta = diff(original(), rewired())
        assert delta.added == ["netlib"]
        assert delta.edges_gained == [("util", "netlib")]
        assert delta.edges_lost == []

    def test_removals_read_from_the_other_side(self):
        delta = diff(rewired(), original())
        assert delta.removed == ["netlib"]
        assert delta.edges_lost == [("util", "netlib")]


class TestImpact:
    def test_the_rewired_edge_invalidates_its_closure(self):
        delta = diff(original(), rewired())
        assert cache_impact(rewired(), delta) == [
            "app",
            "installer",
            "util",
        ]

    def test_base_survives_the_rewire(self):
        delta = diff(original(), rewired())
        assert "base" not in cache_impact(rewired(), delta)

    def test_the_page_counts_the_quiet_rebuild(self):
        page = review_page(original(), rewired())
        assert "added: netlib" in page
        assert "edge gained: util -> netlib" in page
        assert (
            "cache impact: 3 existing targets will miss "
            "(app, installer, util)" in page
        )
