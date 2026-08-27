from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.hedging import HedgePolicy, best_delay, run_action

PROFILE = [
    *[(10, 10)] * 8,
    (12, 10),
    (90, 10),
]


class TestOneAction:
    def test_a_fast_primary_never_fires_the_hedge(self):
        outcome = run_action(10, 10, delay=15)
        assert not outcome.hedge_fired
        assert outcome.finish == 10
        assert outcome.duplicate_ticks == 0

    def test_the_straggler_is_amputated_by_the_backup(self):
        outcome = run_action(90, 10, delay=15)
        assert outcome.hedge_won
        assert outcome.finish == 25
        assert outcome.duplicate_ticks == 25

    def test_a_primary_that_barely_wins_burns_the_backup(self):
        outcome = run_action(20, 10, delay=15)
        assert outcome.hedge_fired
        assert not outcome.hedge_won
        assert outcome.finish == 20
        assert outcome.duplicate_ticks == 5

    def test_nonsense_latencies_are_refused(self):
        with pytest.raises(Invalid):
            run_action(0, 10, delay=1)


class TestThePolicy:
    def test_the_tail_shrinks_and_the_duplicates_are_counted(self):
        worst, duplicates, fired = HedgePolicy(delay=15).simulate(
            PROFILE
        )
        assert worst == 25
        assert duplicates == 25
        assert fired == 1

    def test_a_zero_delay_doubles_everything(self):
        _, duplicates, fired = HedgePolicy(delay=0).simulate(
            PROFILE
        )
        assert fired == len(PROFILE)
        assert duplicates > 0

    def test_a_huge_delay_never_fires(self):
        worst, duplicates, fired = HedgePolicy(delay=100).simulate(
            PROFILE
        )
        assert (worst, duplicates, fired) == (90, 0, 0)

    def test_an_empty_profile_is_refused(self):
        with pytest.raises(Invalid):
            HedgePolicy(delay=5).simulate([])


class TestBestDelay:
    def test_the_report_names_the_minimizing_delay(self):
        verdict = best_delay(PROFILE, candidates=[0, 15, 100])
        assert verdict.startswith("delay 15:")
        assert "slowest action 25" in verdict
        assert "the minimum over the candidates" in verdict

    def test_no_candidates_is_refused(self):
        with pytest.raises(Invalid):
            best_delay(PROFILE, candidates=[])
