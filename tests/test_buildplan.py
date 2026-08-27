from __future__ import annotations

import pytest

from forge.buildplan import BuildPlanner
from forge.errors import Invalid
from forge.graph import Graph


def planner(**overrides) -> BuildPlanner:
    graph = Graph()
    graph.declare("core")
    graph.declare("app", needs=("core",))
    graph.declare("tool", needs=("core",))
    graph.declare("docs")
    settings = {
        "graph": graph,
        "sources_of": {
            "core": ("core.c",),
            "app": ("app.c",),
            "tool": ("tool.c",),
            "docs": ("guide.md",),
        },
        "cost_of": {"core": 30, "app": 20, "tool": 15, "docs": 2},
    }
    settings.update(overrides)
    return BuildPlanner(**settings)


class TestThePlan:
    def test_the_cone_is_priced_with_reasons(self):
        plan = planner().plan(("core.c",))
        assert plan.startswith(
            "3 target(s) run, 1 hit the cache; 65 tick(s) "
            "predicted"
        )
        assert "run core: reads core.c (30 ticks)" in plan
        assert "run app: downstream of core (20 ticks)" in plan

    def test_a_leaf_edit_stays_small(self):
        plan = planner().plan(("guide.md",))
        assert plan.startswith(
            "1 target(s) run, 3 hit the cache; 2 tick(s)"
        )

    def test_an_untouched_change_runs_nothing(self):
        plan = planner().plan(("README",))
        assert plan.startswith(
            "0 target(s) run, 4 hit the cache; 0 tick(s)"
        )

    def test_no_changes_is_refused(self):
        with pytest.raises(Invalid):
            planner().plan(())


class TestHonestUnknowns:
    def test_the_hermetic_hole_is_an_unknown_not_a_guess(self):
        chosen = planner(hermetic_holes={"app"})
        plan = chosen.plan(("core.c",))
        assert (
            "run app: downstream of core (cost unknown, "
            "hermetic hole)"
        ) in plan
        assert "45 tick(s) predicted plus 1 unknown(s)" in plan
        assert "keeps the rest of the table credible" in plan

    def test_a_costless_target_is_refused_outright(self):
        chosen = planner(cost_of={"core": 30})
        with pytest.raises(Invalid):
            chosen.plan(("core.c",))
