from __future__ import annotations

import pytest

from forge.carveout import CarvePlan
from forge.errors import Invalid
from forge.graph import Graph


def monorepo() -> Graph:
    graph = Graph()
    graph.declare("base/log")
    graph.declare("search/index", needs=("base/log",))
    graph.declare("search/rank", needs=("search/index",))
    graph.declare("ads/serve", needs=("search/rank", "base/log"))
    graph.declare("web/front", needs=("search/rank",))
    return graph


def plan(packages: set[str]) -> CarvePlan:
    return CarvePlan(
        graph=monorepo(), carve_packages=packages
    )


class TestTheBoundary:
    def test_outbound_edges_are_the_carves_shopping_list(self):
        chosen = plan({"search"})
        assert chosen.outbound() == [
            "search/index -> base/log"
        ]

    def test_inbound_edges_are_other_peoples_work(self):
        chosen = plan({"search"})
        assert chosen.inbound() == [
            "ads/serve -> search/rank",
            "web/front -> search/rank",
        ]

    def test_an_empty_carve_is_refused(self):
        with pytest.raises(Invalid):
            plan(set())


class TestTheVerdict:
    def test_the_verdict_weighs_inbound_triple(self):
        verdict = plan({"search"}).verdict()
        assert verdict.startswith(
            "carve search: 1 outbound, 2 inbound, effort 7"
        )
        assert "publish or pin" in verdict
        assert "their migration, your calendar" in verdict

    def test_a_leafless_carve_is_cheap(self):
        verdict = plan({"web"}).verdict()
        assert "1 outbound, 0 inbound, effort 1" in verdict

    def test_a_cross_boundary_cycle_is_refused(self):
        graph = Graph()
        graph.declare("auth/token")
        graph.declare("billing/pay", needs=("auth/token",))
        graph.declare("auth/audit", needs=("billing/pay",))
        chosen = CarvePlan(
            graph=graph, carve_packages={"auth"}
        )
        verdict = chosen.verdict()
        assert verdict.startswith("REFUSED: billing")
        assert "neither repo could ever build first" in verdict
