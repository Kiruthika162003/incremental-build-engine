from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.restatement import MetricHistory


def history() -> MetricHistory:
    built = MetricHistory(metric="cache-hit-rate")
    built.publish("2031-q1", 94.0)
    built.publish("2031-q2", 95.5)
    return built


class TestPublishing:
    def test_overwriting_is_routed_to_restatement(self):
        chosen = history()
        with pytest.raises(Invalid) as caught:
            chosen.publish("2031-q1", 80.0)
        assert "not overwriting" in str(caught.value)


class TestRestating:
    def test_both_series_survive_side_by_side(self):
        chosen = history()
        verdict = chosen.restate(
            "2031-q1", 81.0, defect="meter counted dirty hits"
        )
        assert verdict == (
            "2031-q1: published 94.0 stands, restated 81.0 "
            "beside it (meter counted dirty hits)"
        )
        read = chosen.read("2031-q1")
        assert "RESTATED" in read
        assert "originally published 94.0" in read

    def test_the_unrestated_period_reads_as_published(self):
        assert history().read("2031-q2") == (
            "2031-q2: 95.5 (as published)"
        )

    def test_a_defectless_restatement_is_a_rewrite(self):
        with pytest.raises(Invalid) as caught:
            history().restate("2031-q1", 81.0, defect="  ")
        assert "rewrite for convenience" in str(caught.value)

    def test_re_restating_demands_the_paper_trail(self):
        chosen = history()
        chosen.restate("2031-q1", 81.0, defect="dirty hits")
        with pytest.raises(Invalid) as caught:
            chosen.restate("2031-q1", 82.0, defect="also skew")
        assert "name the prior restatement" in str(caught.value)
        verdict = chosen.restate(
            "2031-q1",
            82.0,
            defect="also skew",
            supersedes_note="the dirty-hits restatement",
        )
        assert "restated 82.0" in verdict

    def test_restating_the_unpublished_is_refused(self):
        with pytest.raises(Invalid):
            history().restate("2030-q4", 1.0, defect="x")


class TestTheLabel:
    def test_the_label_counts_and_defends_both_series(self):
        chosen = history()
        chosen.restate("2031-q1", 81.0, defect="dirty hits")
        label = chosen.series_label()
        assert label.startswith(
            "cache-hit-rate: 1 of 2 period(s) restated"
        )
        assert "argument waiting to happen" in label

    def test_a_clean_history_says_so(self):
        assert history().series_label() == (
            "cache-hit-rate: as published throughout"
        )
