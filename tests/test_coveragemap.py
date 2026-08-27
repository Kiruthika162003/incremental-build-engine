from __future__ import annotations

import pytest

from forge.coveragemap import CoverageMap
from forge.errors import Invalid, Missing
from forge.graph import Graph


def repo() -> CoverageMap:
    graph = Graph()
    graph.declare("core")
    graph.declare("api", needs=("core",))
    graph.declare("app", needs=("api",))
    graph.declare("leafutil")
    built = CoverageMap(graph=graph)
    built.record(
        "api_test", targets={"api"}, pct={"api": 80}
    )
    built.record(
        "app_test", targets={"app", "api"}, pct={"app": 60, "api": 70}
    )
    return built


class TestUntested:
    def test_blast_radius_ranks_the_untested(self):
        untested = repo().untested(
            ["core", "api", "app", "leafutil"]
        )
        assert untested == ["core", "leafutil"]

    def test_the_best_coverage_wins_per_target(self):
        assert repo().coverage_pct["api"] == 80

    def test_percentages_stay_percentages(self):
        with pytest.raises(Invalid):
            repo().record("bad", targets=set(), pct={"x": 130})


class TestDrops:
    def test_the_fall_carries_both_numbers(self):
        built = repo()
        built.snapshot()
        built.coverage_pct["app"] = 40
        assert built.fell_since_snapshot() == ["app: 60% -> 40%"]

    def test_no_snapshot_refuses_the_comparison(self):
        with pytest.raises(Invalid):
            repo().fell_since_snapshot()


class TestDeletion:
    def test_the_orphans_are_answered_before_the_deletion(self):
        assert repo().deletion_orphans("app_test") == ["app"]

    def test_a_covered_target_survives_its_redundant_test(self):
        assert "api" not in repo().deletion_orphans("api_test")

    def test_deleting_the_unknown_is_refused(self):
        with pytest.raises(Missing):
            repo().deletion_orphans("ghost_test")


class TestTheGate:
    def test_the_gate_is_per_target_not_global(self):
        built = repo()
        assert "clears its 50% floor" in built.gate("api", floor=50)
        refusal = built.gate("core", floor=50)
        assert refusal.startswith("REFUSED: core at 0%")
        assert "a global gate would have let this slide" in refusal
