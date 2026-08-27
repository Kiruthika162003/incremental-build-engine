from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.watchbudget import WatchedDir, blindness_check, plan

TREE = [
    WatchedDir("src/core", 400),
    WatchedDir("src/app", 150),
    WatchedDir("tools", 12),
    WatchedDir("docs", 3),
    WatchedDir("attic", 1),
]


class TestThePlan:
    def test_the_busiest_directories_get_the_eyes(self):
        report = plan(TREE, watch_limit=2)
        assert report.startswith("2 watched, 3 polled")
        assert "poll tools every" in report
        assert "poll src/core" not in report

    def test_cold_directories_poll_lazily(self):
        report = plan(TREE, watch_limit=2)
        assert "poll docs every 86 tick(s)" in report
        assert "poll attic every 220 tick(s)" in report

    def test_the_boundary_pair_is_named_for_review(self):
        report = plan(TREE, watch_limit=2)
        assert (
            "src/app (150/day) is the coldest watched; tools "
            "(12/day) is the hottest polled"
        ) in report

    def test_zero_limits_and_empty_trees_are_refused(self):
        with pytest.raises(Invalid):
            plan(TREE, watch_limit=0)
        with pytest.raises(Invalid):
            plan([], watch_limit=5)


class TestBlindness:
    def test_the_silently_unwatched_directory_is_named(self):
        verdict = blindness_check(
            TREE,
            watch_limit=2,
            actually_watched={"src/core"},
        )
        assert verdict.startswith("BLIND: src/app")
        assert "not slow, blind" in verdict

    def test_a_live_budget_passes(self):
        assert blindness_check(
            TREE,
            watch_limit=2,
            actually_watched={"src/core", "src/app"},
        ) == "every budgeted watch is live"
