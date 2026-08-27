from __future__ import annotations

import pytest

from forge.burndown import Burndown
from forge.errors import Invalid


def sprint() -> Burndown:
    chart = Burndown(planned_points=40)
    chart.record_day(burned=10)
    chart.record_day(burned=12, scope_added=15)
    chart.record_day(burned=10, scope_added=8)
    chart.record_day(burned=10, scope_added=7)
    return chart


class TestTheTwoSeries:
    def test_the_flat_line_explains_itself(self):
        chart = sprint()
        assert chart.remaining() == 28
        assert sum(chart.burned) == 42
        assert sum(chart.added) == 30

    def test_negative_burn_is_refused_as_chart_rigging(self):
        chart = Burndown(planned_points=10)
        with pytest.raises(Invalid) as caught:
            chart.record_day(burned=-5)
        assert "never as negative burn" in str(caught.value)


class TestTheSummary:
    def test_door_control_is_named_when_the_burn_held(self):
        summary = sprint().closing_summary()
        assert summary.startswith(
            "planned 40, burned 42, absorbed 30, 28 remaining"
        )
        assert "door control, not estimation" in summary

    def test_estimation_is_named_when_the_scope_held(self):
        chart = Burndown(planned_points=40)
        chart.record_day(burned=8)
        chart.record_day(burned=9)
        summary = chart.closing_summary()
        assert "estimation, not door control" in summary

    def test_an_unrecorded_sprint_has_no_summary(self):
        with pytest.raises(Invalid):
            Burndown(planned_points=10).closing_summary()
