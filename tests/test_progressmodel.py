from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.progressmodel import ProgressModel


def model() -> ProgressModel:
    return ProgressModel(
        modeled={"a": 10, "b": 10, "c": 10, "d": 10}
    )


class TestEstimation:
    def test_the_cold_estimate_trusts_the_model(self):
        assert model().remaining_estimate() == 40.0

    def test_a_slow_machine_bends_the_bar(self):
        bar = model()
        bar.finish("a", actual=20)
        assert bar.speed_factor == 1.4
        assert bar.remaining_estimate() == 42.0

    def test_a_fast_machine_bends_it_the_other_way(self):
        bar = model()
        bar.finish("a", actual=5)
        assert bar.speed_factor == 0.8
        assert bar.remaining_estimate() == 24.0

    def test_evidence_accumulates_with_smoothing(self):
        bar = model()
        bar.finish("a", actual=20)
        bar.finish("b", actual=20)
        assert bar.speed_factor == 1.64

    def test_strangers_and_repeats_are_refused(self):
        bar = model()
        with pytest.raises(Invalid):
            bar.finish("ghost", actual=1)
        bar.finish("a", actual=10)
        with pytest.raises(Invalid):
            bar.finish("a", actual=10)

    def test_empty_and_nonpositive_models_are_refused(self):
        with pytest.raises(Invalid):
            ProgressModel(modeled={})
        with pytest.raises(Invalid):
            ProgressModel(modeled={"a": 0})


class TestTheGrade:
    def finished_run(self, actuals: list[int]) -> ProgressModel:
        bar = model()
        for name, actual in zip("abcd", actuals, strict=True):
            bar.finish(name, actual)
        return bar

    def test_a_true_model_grades_near_zero(self):
        bar = self.finished_run([10, 10, 10, 10])
        errors = [error for _, error in bar.error_curve()]
        assert all(abs(error) < 0.01 for error in errors)

    def test_a_throttled_machine_overpromises_early(self):
        bar = self.finished_run([20, 20, 20, 20])
        first_error = bar.error_curve()[0][1]
        assert first_error < 0
        assert "worst overpromise" in bar.honesty_line()

    def test_the_bar_bends_toward_truth(self):
        bar = self.finished_run([20, 20, 20, 20])
        errors = [error for _, error in bar.error_curve()]
        assert abs(errors[2]) < abs(errors[0])

    def test_grading_an_unfinished_build_is_refused(self):
        bar = model()
        bar.finish("a", actual=10)
        with pytest.raises(Invalid, match="grade it later"):
            bar.error_curve()
