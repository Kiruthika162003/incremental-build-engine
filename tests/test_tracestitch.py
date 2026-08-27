from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.tracestitch import Span, TraceStitcher


def full_trace() -> TraceStitcher:
    stitcher = TraceStitcher()
    stitcher.collect(
        Span("t1", "coordinator", 0, 2, "accepted build")
    )
    stitcher.collect(Span("t1", "worker", 5, 90, "ran compile"))
    stitcher.collect(Span("t1", "cache", 3, 1, "miss"))
    stitcher.collect(Span("t1", "store", 96, 4, "uploaded"))
    stitcher.collect(Span("t2", "coordinator", 0, 1, "other"))
    return stitcher


class TestStitching:
    def test_the_timeline_orders_by_declared_start(self):
        report = full_trace().timeline("t1")
        lines = report.splitlines()
        assert lines[0].startswith(
            "t1: 4 span(s) across 4 service(s)"
        )
        assert "coordinator" in lines[1]
        assert "cache" in lines[2]
        assert "worker" in lines[3]

    def test_other_traces_stay_out_of_the_story(self):
        assert "other" not in full_trace().timeline("t1")

    def test_an_unknown_trace_is_refused_with_both_readings(self):
        with pytest.raises(Invalid) as caught:
            full_trace().timeline("ghost")
        assert "either the id is wrong or everything is blind" in (
            str(caught.value)
        )


class TestTheGaps:
    def test_the_blind_service_is_named(self):
        stitcher = TraceStitcher()
        stitcher.collect(
            Span("t3", "coordinator", 0, 2, "accepted")
        )
        stitcher.collect(Span("t3", "worker", 4, 50, "ran"))
        report = stitcher.timeline("t3")
        assert "BLIND: cache, store contributed no span" in report
        assert "(partial, and saying so)" in report

    def test_clock_skew_is_its_own_incident(self):
        stitcher = TraceStitcher()
        stitcher.collect(
            Span("t4", "coordinator", 10, 2, "accepted")
        )
        stitcher.collect(Span("t4", "worker", 4, 5, "ran"))
        report = stitcher.timeline("t4")
        assert (
            "CLOCK SKEW: worker starts at 4 before the "
            "coordinator's 10"
        ) in report
        assert "its own incident" in report

    def test_a_sane_ordering_reports_no_skew(self):
        assert "CLOCK SKEW" not in full_trace().timeline("t1")

    def test_negative_spans_are_refused(self):
        with pytest.raises(Invalid):
            TraceStitcher().collect(
                Span("t", "worker", 0, -1, "odd")
            )
