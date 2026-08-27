from __future__ import annotations

import pytest

from forge.autoscale import AutoScaler
from forge.errors import Invalid


def farm(**overrides) -> AutoScaler:
    settings = {
        "min_workers": 2,
        "max_workers": 10,
        "depth_per_worker": 3,
        "cool_ticks": 3,
    }
    settings.update(overrides)
    return AutoScaler(**settings)


class TestScalingUp:
    def test_the_burst_is_answered_immediately(self):
        fleet = farm()
        assert fleet.tick(queue_depth=18) == 6
        assert fleet.scale_ups == 1
        assert "scale up 2 -> 6 (depth 18)" in fleet.events

    def test_the_ceiling_holds_under_any_burst(self):
        fleet = farm()
        assert fleet.tick(queue_depth=500) == 10

    def test_a_calm_queue_stays_at_the_floor(self):
        fleet = farm()
        assert fleet.tick(queue_depth=0) == 2


class TestScalingDown:
    def test_one_quiet_tick_does_not_shrink_the_fleet(self):
        fleet = farm()
        fleet.tick(queue_depth=18)
        assert fleet.tick(queue_depth=0) == 6

    def test_the_cool_period_must_fill_completely(self):
        fleet = farm()
        fleet.tick(queue_depth=18)
        fleet.tick(queue_depth=0)
        fleet.tick(queue_depth=0)
        assert fleet.workers == 6
        assert fleet.tick(queue_depth=0) == 2
        assert fleet.scale_downs == 1

    def test_a_flapping_queue_never_shrinks_the_fleet(self):
        fleet = farm()
        fleet.tick(queue_depth=18)
        for _ in range(4):
            fleet.tick(queue_depth=0)
            fleet.tick(queue_depth=18)
        assert fleet.workers == 6
        assert fleet.scale_downs == 0


class TestTheBill:
    def test_both_currencies_appear(self):
        fleet = farm()
        fleet.tick(queue_depth=18)
        fleet.tick(queue_depth=1)
        bill = fleet.bill()
        assert "1 scale-up(s)" in bill
        assert "idle worker tick(s)" in bill
        assert "queued build tick(s)" in bill

    def test_overload_is_billed_as_queued_ticks(self):
        fleet = farm(max_workers=3)
        fleet.tick(queue_depth=30)
        assert fleet.queued_ticks == 27

    def test_overnight_idle_is_billed_to_the_floor_fleet(self):
        fleet = farm()
        for _ in range(5):
            fleet.tick(queue_depth=0)
        assert fleet.idle_ticks == 10


class TestRefusals:
    def test_a_zero_worker_floor_is_refused(self):
        with pytest.raises(Invalid):
            farm(min_workers=0)

    def test_a_negative_depth_is_refused(self):
        with pytest.raises(Invalid):
            farm().tick(queue_depth=-1)
