from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.spotmath import SpotDay


def calm_day(**overrides) -> SpotDay:
    settings = {
        "actions": 100,
        "ticks_per_action": 20,
        "on_demand_rate": 1.0,
        "spot_discount": 0.7,
        "preemptions": 5,
        "respawn_gap_ticks": 10,
    }
    settings.update(overrides)
    return SpotDay(**settings)


class TestTheBills:
    def test_the_waste_is_progress_plus_the_gap(self):
        day = calm_day()
        assert day.wasted_ticks() == 5 * (10 + 10)

    def test_checkpoints_keep_the_progress(self):
        day = calm_day(checkpointed=True)
        assert day.wasted_ticks() == 50

    def test_a_calm_day_on_spot_is_cheap(self):
        day = calm_day()
        assert day.spot_bill() == pytest.approx(630.0)
        assert day.on_demand_bill() == pytest.approx(2000.0)
        assert day.verdict().startswith("spot wins")

    def test_a_stormy_day_drowns_the_discount(self):
        day = calm_day(preemptions=100, respawn_gap_ticks=400)
        verdict = day.verdict()
        assert verdict.startswith("on-demand wins")
        assert "the discount drowned in rework" in verdict


class TestBreakEven:
    def test_the_break_even_is_computed_not_felt(self):
        assert calm_day().break_even_preemptions() == 233

    def test_checkpoints_move_the_break_even(self):
        without = calm_day().break_even_preemptions()
        with_ckpt = calm_day(
            checkpointed=True
        ).break_even_preemptions()
        assert with_ckpt == 466
        assert with_ckpt == 2 * without

    def test_free_preemptions_have_no_break_even(self):
        day = calm_day(checkpointed=True, respawn_gap_ticks=0)
        with pytest.raises(Invalid):
            day.break_even_preemptions()


class TestRefusals:
    def test_a_flickering_fleet_is_refused(self):
        with pytest.raises(Invalid):
            calm_day(preemptions=101)

    def test_a_full_price_discount_is_refused(self):
        with pytest.raises(Invalid):
            calm_day(spot_discount=1.0)
