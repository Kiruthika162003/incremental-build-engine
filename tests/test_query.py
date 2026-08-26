from __future__ import annotations

import pytest

from forge.errors import Missing
from forge.graph import Graph
from forge.query import Query


def layered() -> Query:
    graph = Graph()
    graph.declare("base")
    graph.declare("util", needs=("base",))
    graph.declare("net", needs=("base",))
    graph.declare("db", needs=("util",))
    graph.declare("api", needs=("net", "db"))
    graph.declare("app", needs=("api", "util"))
    return Query(graph=graph)


class TestDeps:
    def test_deps_walks_the_whole_cone(self):
        assert layered().deps("app") == [
            "api",
            "base",
            "db",
            "net",
            "util",
        ]

    def test_depth_one_is_the_direct_needs(self):
        assert layered().deps("app", depth=1) == ["api", "util"]

    def test_leaves_have_no_deps(self):
        assert layered().deps("base") == []


class TestRdeps:
    def test_rdeps_is_the_blast_radius(self):
        assert layered().rdeps("base") == [
            "api",
            "app",
            "db",
            "net",
            "util",
        ]

    def test_depth_one_is_who_uses_it_directly(self):
        assert layered().rdeps("util", depth=1) == ["app", "db"]

    def test_the_top_has_no_rdeps(self):
        assert layered().rdeps("app") == []


class TestPaths:
    def test_somepath_finds_the_shortest_chain(self):
        assert layered().somepath("app", "base") == [
            "app",
            "util",
            "base",
        ]

    def test_unrelated_targets_have_no_path(self):
        assert layered().somepath("net", "db") is None

    def test_allpaths_counts_the_tangle(self):
        assert layered().allpaths("app", "base") == 3

    def test_explain_edge_reads_aloud(self):
        assert layered().explain_edge("app", "base") == (
            "app -> util -> base (3 paths in total)"
        )

    def test_explaining_a_missing_edge_is_refused(self):
        with pytest.raises(Missing, match="by any path"):
            layered().explain_edge("net", "db")


class TestShape:
    def test_roots_are_what_nothing_needs(self):
        assert layered().roots() == ["app"]

    def test_leaves_are_what_needs_nothing(self):
        assert layered().leaves() == ["base"]
