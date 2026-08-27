from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.graph import Graph
from forge.graphstats import GraphStats


def chain(length: int) -> GraphStats:
    graph = Graph()
    previous = None
    for number in range(length):
        name = f"n{number}"
        graph.declare(
            name, needs=(previous,) if previous else ()
        )
        previous = name
    return GraphStats(graph=graph)


def funnel() -> GraphStats:
    graph = Graph()
    graph.declare("corelib")
    for number in range(4):
        graph.declare(f"user{number}", needs=("corelib",))
    return GraphStats(graph=graph)


class TestShape:
    def test_depth_is_the_longest_chain(self):
        assert chain(5).depth() == 4

    def test_fan_in_marks_the_funnel(self):
        assert funnel().fan_in()["corelib"] == 4

    def test_fan_out_marks_the_consumers(self):
        stats = funnel()
        assert stats.fan_out()["user0"] == 1
        assert stats.fan_out()["corelib"] == 0

    def test_chokepoints_carry_their_counts(self):
        assert funnel().chokepoints() == [("corelib", 4)]


class TestVerdicts:
    def test_the_chain_reads_deep_and_narrow(self):
        verdict = chain(6).shape_verdict()
        assert verdict.startswith("deep and narrow (depth 5)")

    def test_the_funnel_names_its_chokepoint(self):
        verdict = funnel().shape_verdict()
        assert verdict.startswith("funnelled: 1 chokepoint(s)")
        assert "corelib" in verdict
        assert "by arithmetic" in verdict

    def test_the_flat_fleet_reads_wide_and_shallow(self):
        graph = Graph()
        for number in range(6):
            graph.declare(f"leaf{number}")
        verdict = GraphStats(graph=graph).shape_verdict()
        assert verdict.startswith("wide and shallow")

    def test_an_empty_graph_has_no_shape(self):
        with pytest.raises(Invalid):
            GraphStats(graph=Graph()).shape_verdict()
