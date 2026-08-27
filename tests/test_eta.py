from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.eta import EtaEstimator


def estimator() -> EtaEstimator:
    return EtaEstimator(drain_per_tick=10)


class TestPromises:
    def test_the_first_promise_admits_it_has_no_record(self):
        line = estimator().promise(work_ahead=300)
        assert line == (
            "starts in ~30 tick(s) (no record yet; treat the "
            "number gently)"
        )

    def test_the_error_bar_comes_from_the_record(self):
        chosen = estimator()
        chosen.score(promised=30, actual=38)
        chosen.score(promised=20, actual=17)
        assert chosen.promise(300) == (
            "starts in 30 +/- 8 tick(s)"
        )

    def test_a_stuck_queue_is_refused(self):
        with pytest.raises(Invalid):
            EtaEstimator(drain_per_tick=0)


class TestScoring:
    def test_late_widens_the_bar(self):
        chosen = estimator()
        verdict = chosen.score(promised=30, actual=45)
        assert verdict == (
            "late by 15: the next error bar widens to cover it"
        )

    def test_early_is_a_polite_lie(self):
        verdict = estimator().score(promised=30, actual=22)
        assert "polite, but still a lie" in verdict

    def test_exact_narrows_the_future(self):
        assert "earns a narrower bar" in estimator().score(
            promised=30, actual=30
        )

    def test_the_window_forgets_ancient_errors(self):
        chosen = estimator()
        chosen.score(promised=0, actual=50)
        for _ in range(5):
            chosen.score(promised=10, actual=11)
        assert chosen.error_bar() == 1


class TestTheGrade:
    def test_the_public_grade_counts_all_three_columns(self):
        chosen = estimator()
        chosen.score(30, 30)
        chosen.score(30, 40)
        chosen.score(30, 25)
        grade = chosen.public_grade()
        assert grade.startswith(
            "3 promise(s): 1 exact, 1 early, 1 late"
        )
        assert "contempt is compounding" in grade

    def test_an_unscored_estimator_has_no_grade(self):
        with pytest.raises(Invalid):
            estimator().public_grade()
