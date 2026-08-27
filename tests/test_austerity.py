from __future__ import annotations

import pytest

from forge.austerity import Program, austerity_plan
from forge.errors import Invalid

PREWARM = Program(
    name="prewarming", cost_per_week=100, return_per_week=700
)
HEDGE = Program(
    name="hedging", cost_per_week=200, return_per_week=600
)
HUNCH = Program(
    name="speculative-fetch",
    cost_per_week=150,
    return_per_week=None,
)
CLEANROOM = Program(
    name="nightly-cleanroom",
    cost_per_week=80,
    return_per_week=0,
    insurance=True,
)


class TestTheCutLine:
    def test_the_best_ratio_survives_the_deepest_cut(self):
        plan = austerity_plan(
            [HEDGE, PREWARM, HUNCH, CLEANROOM],
            budget_per_week=200,
        )
        assert "keep prewarming: returns 7.0" in plan
        assert "suspend hedging: returns 3.0" in plan

    def test_the_unmeasured_program_sorts_last_by_policy(self):
        plan = austerity_plan(
            [HUNCH, PREWARM, HEDGE], budget_per_week=300
        )
        assert (
            "suspend speculative-fetch: never measured, "
            "sorted last by policy"
        ) in plan
        assert "keep hedging" in plan

    def test_a_roomy_budget_keeps_everything_measurable(self):
        plan = austerity_plan(
            [PREWARM, HEDGE, HUNCH], budget_per_week=1000
        )
        assert "3 kept, 0 suspended" in plan


class TestInsurance:
    def test_insurance_is_never_auto_cut(self):
        plan = austerity_plan(
            [PREWARM, CLEANROOM], budget_per_week=90
        )
        assert "1 insurance held for a human" in plan
        assert (
            "insurance nightly-cleanroom: priced by the "
            "incident it prevents"
        ) in plan
        assert "suspend nightly-cleanroom" not in plan

    def test_insurance_spend_comes_off_the_top(self):
        plan = austerity_plan(
            [PREWARM, CLEANROOM], budget_per_week=180
        )
        assert "keep prewarming" in plan


class TestRefusals:
    def test_an_empty_program_list_is_refused(self):
        with pytest.raises(Invalid):
            austerity_plan([], budget_per_week=100)

    def test_a_negative_budget_is_a_shutdown(self):
        with pytest.raises(Invalid):
            austerity_plan([PREWARM], budget_per_week=-1)
