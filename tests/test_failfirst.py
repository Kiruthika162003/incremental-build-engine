from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.failfirst import (
    FailFirstScheduler,
    FailureHistory,
)


def seasoned_history() -> FailureHistory:
    history = FailureHistory()
    for _ in range(5):
        history.record("test_api", True)
        history.record("test_zpipeline", False)
    history.record("test_zpipeline", True)
    return history


def scheduler() -> FailFirstScheduler:
    return FailFirstScheduler(
        history=seasoned_history(),
        costs={
            "test_api": 60,
            "test_zpipeline": 30,
            "test_middle": 10,
        },
    )


class TestScoring:
    def test_a_clean_record_scores_near_zero(self):
        assert seasoned_history().failure_score(
            "test_api"
        ) == 0.0

    def test_a_fresh_test_is_a_risk_not_a_pass(self):
        assert seasoned_history().failure_score(
            "test_brand_new"
        ) == 0.5

    def test_recent_passes_outweigh_old_failures(self):
        history = FailureHistory()
        for _ in range(5):
            history.record("test_summer", False)
        for _ in range(5):
            history.record("test_summer", True)
        assert history.failure_score("test_summer") < 0.35

    def test_the_window_forgets_the_distant_past(self):
        history = FailureHistory()
        for _ in range(20):
            history.record("test_reformed", False)
        for _ in range(10):
            history.record("test_reformed", True)
        assert history.failure_score("test_reformed") == 0.0


class TestOrdering:
    def test_the_likeliest_failure_runs_first(self):
        assert scheduler().order() == [
            "test_zpipeline",
            "test_middle",
            "test_api",
        ]

    def test_an_empty_suite_is_refused(self):
        with pytest.raises(Invalid):
            FailFirstScheduler(
                history=FailureHistory(), costs={}
            ).order()


class TestTheSavings:
    def test_the_report_prices_the_ordering(self):
        report = scheduler().savings_report(
            failing={"test_zpipeline"}
        )
        assert report == (
            "first red at 30 ticks with history order, "
            "100 alphabetical: 70 tick(s) returned to the "
            "developer"
        )

    def test_a_green_run_buys_nothing_and_says_so(self):
        assert "buys nothing today" in scheduler().savings_report(
            failing=set()
        )
