from __future__ import annotations

import pytest

from forge.errors import Invalid, Missing
from forge.graph import Graph
from forge.sparsecheckout import SparsePlanner, directory_of

TREE = {
    "app/src": 40,
    "core/src": 120,
    "search/src": 800,
    "billing/src": 600,
    "tools/build": 15,
    ".": 5,
}


def planner() -> SparsePlanner:
    graph = Graph()
    graph.declare("core")
    graph.declare("app", needs=("core",))
    graph.declare("search", needs=("core",))
    return SparsePlanner(
        graph=graph,
        reads_by_target={
            "core": ("core/src/lib.c",),
            "app": ("app/src/main.c",),
            "search": ("search/src/index.c",),
        },
        tree_files=dict(TREE),
    )


class TestTheProfile:
    def test_the_profile_is_the_closure_plus_the_roots(self):
        assert planner().profile(("app",)) == [
            "app/src",
            "core/src",
            "tools/build",
        ]

    def test_the_root_file_maps_to_dot(self):
        assert directory_of("README.md") == "."

    def test_a_ghost_target_is_refused(self):
        with pytest.raises(Missing):
            planner().profile(("ghost",))

    def test_an_empty_want_is_refused(self):
        with pytest.raises(Invalid):
            planner().profile(())


class TestTheSavings:
    def test_the_savings_line_sells_the_practice(self):
        line = planner().savings(("app",))
        assert line == (
            "3 directorie(s), 175 of 1580 files "
            "(11% of the monorepo)"
        )

    def test_wanting_everything_still_skips_strangers(self):
        line = planner().savings(("app", "search"))
        assert "975 of 1580" in line


class TestTheMiss:
    def test_an_outside_reach_gets_the_amendment(self):
        verdict = planner().explain_miss(
            ("app",), "billing/src/invoice.c"
        )
        assert "outside the profile" in verdict
        assert "add billing/src to the profile" in verdict

    def test_an_inside_miss_is_not_blamed_on_sparseness(self):
        verdict = planner().explain_miss(
            ("app",), "core/src/deleted.c"
        )
        assert "not a sparseness problem" in verdict
