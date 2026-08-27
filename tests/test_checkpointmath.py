from __future__ import annotations

import pytest

from forge.checkpointmath import (
    expected_bill,
    plan,
    sqrt_law_interval,
)
from forge.errors import Invalid


class TestTheBill:
    def test_frequent_checkpoints_pay_in_overhead(self):
        eager = expected_bill(
            run_ticks=600,
            interval=10,
            checkpoint_cost=5,
            restore_cost=8,
            preemptions_per_run=2,
        )
        assert eager == 60 * 5 + 2 * (5 + 8)

    def test_rare_checkpoints_pay_in_lost_work(self):
        lazy = expected_bill(
            run_ticks=600,
            interval=600,
            checkpoint_cost=5,
            restore_cost=8,
            preemptions_per_run=2,
        )
        assert lazy == 5 + 2 * (300 + 8)

    def test_the_interval_cannot_exceed_the_run(self):
        with pytest.raises(Invalid):
            expected_bill(100, 200, 1, 1, 1.0)


class TestTheLaw:
    def test_the_optimum_grows_with_checkpoint_cost(self):
        cheap = sqrt_law_interval(2, 0.01)
        dear = sqrt_law_interval(50, 0.01)
        assert dear > cheap

    def test_the_optimum_shrinks_with_storminess(self):
        calm = sqrt_law_interval(5, 0.001)
        storm = sqrt_law_interval(5, 0.1)
        assert storm < calm

    def test_a_quiet_fleet_breaks_the_law(self):
        with pytest.raises(Invalid):
            sqrt_law_interval(5, 0)


class TestThePlan:
    def test_the_table_names_the_winning_interval(self):
        verdict = plan(
            run_ticks=600,
            checkpoint_cost=5,
            restore_cost=8,
            preemptions_per_run=2,
            candidates=[10, 30, 60, 120, 300, 600],
        )
        assert verdict.startswith("checkpoint every 60 tick(s)")
        assert "the square-root law says 55" in verdict
        assert "the table agrees with the law" in verdict

    def test_no_candidates_is_refused(self):
        with pytest.raises(Invalid):
            plan(600, 5, 8, 2, [])
