from __future__ import annotations

import pytest

from forge.cachewarm import MorningScore, Warmer
from forge.errors import Invalid
from forge.graph import Graph


def overnight() -> Warmer:
    graph = Graph()
    graph.declare("core.c")
    graph.declare("core.o", needs=("core.c",))
    graph.declare("app", needs=("core.o",))
    graph.declare("bench", needs=("core.o",))
    return Warmer(
        graph=graph,
        costs={"core.o": 10, "app": 30, "bench": 25},
    )


class TestPlanning:
    def test_the_cone_of_the_merge_is_the_prediction(self):
        plan = overnight().plan(["core.c"], budget=100)
        assert plan.predicted == ["app", "bench", "core.o"]
        assert plan.budget_used == 65

    def test_the_budget_keeps_the_dearest_first(self):
        plan = overnight().plan(["core.c"], budget=40)
        assert plan.predicted == ["app", "core.o"]

    def test_a_stranger_merge_is_refused(self):
        with pytest.raises(Invalid, match="never heard"):
            overnight().plan(["mystery.c"], budget=10)

    def test_a_nightless_budget_is_refused(self):
        with pytest.raises(Invalid):
            overnight().plan(["core.c"], budget=0)


class TestTheMorning:
    def test_requests_score_warm_or_cold(self):
        score = MorningScore(warmed={"app", "core.o"})
        assert score.request("app") == "warm"
        assert score.request("bench") == "cold"

    def test_the_two_failures_are_priced_apart(self):
        score = MorningScore(warmed={"app", "core.o", "bench"})
        score.request("app")
        score.request("docs")
        assert score.cold_misses() == ["docs"]
        assert score.wasted_warmth() == ["bench", "core.o"]
        assert score.line() == (
            "1 warm, 1 cold (timidity), 2 wasted (guessing)"
        )

    def test_the_diagnosis_points_at_the_dominant_failure(self):
        guessing = MorningScore(warmed={"a", "b", "c"})
        guessing.request("a")
        assert guessing.diagnosis().startswith("guessing")
        timid = MorningScore(warmed=set())
        timid.request("a")
        timid.request("b")
        assert timid.diagnosis().startswith("timid")

    def test_an_exact_prediction_is_left_alone(self):
        exact = MorningScore(warmed={"a"})
        exact.request("a")
        assert exact.diagnosis() == (
            "the prediction was exact; do not touch it"
        )

    def test_balanced_failures_warn_about_opposing_fixes(self):
        balanced = MorningScore(warmed={"a", "b"})
        balanced.request("a")
        balanced.request("c")
        assert "the fixes oppose" in balanced.diagnosis()
