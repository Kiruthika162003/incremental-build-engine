from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.prescale import Prescaler

MONDAY_10 = 10
SUNDAY_3 = 147


def seasoned() -> Prescaler:
    scaler = Prescaler(depth_per_worker=3)
    for week in range(4):
        scaler.observe_week(
            {MONDAY_10: 24 + 3 * week, SUNDAY_3: 0}
        )
    return scaler


class TestLearning:
    def test_the_rush_hour_gets_a_floor(self):
        floor, confidence = seasoned().floor_for(MONDAY_10)
        assert floor == 9
        assert confidence == "confident"

    def test_the_quiet_slot_gets_no_floor(self):
        floor, _ = seasoned().floor_for(SUNDAY_3)
        assert floor == 0

    def test_one_loud_monday_is_low_confidence(self):
        scaler = Prescaler(depth_per_worker=3)
        scaler.observe_week({MONDAY_10: 60})
        _, confidence = scaler.floor_for(MONDAY_10)
        assert confidence == "low confidence (1 week(s))"

    def test_an_unseen_slot_belongs_to_the_reactive_layer(self):
        _, note = seasoned().floor_for(80)
        assert "the reactive layer owns this slot" in note

    def test_bad_slots_and_empty_weeks_are_refused(self):
        scaler = Prescaler(depth_per_worker=3)
        with pytest.raises(Invalid):
            scaler.observe_week({200: 5})
        with pytest.raises(Invalid):
            scaler.observe_week({})


class TestTheDivisionOfLabor:
    def test_the_calendar_and_the_reaction_split_the_burst(self):
        verdict = seasoned().serve_slot(
            MONDAY_10, actual_depth=40
        )
        assert "floor 9 worker(s) (confident)" in verdict
        assert "calendar served 27, reaction served 13" in verdict

    def test_the_week_report_refuses_stolen_valor(self):
        report = seasoned().week_report(
            {MONDAY_10: 40, SUNDAY_3: 2, 80: 6}
        )
        assert report.startswith(
            "calendar served 27, reaction served 21"
        )
        assert "stealing valor" in report

    def test_no_actuals_is_refused(self):
        with pytest.raises(Invalid):
            seasoned().week_report({})
