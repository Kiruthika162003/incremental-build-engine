from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.toolcanary import CanaryRun, in_slice

FLEET = [f"pkg{number}/lib" for number in range(40)]


def sliced(percent: int) -> list[str]:
    return [
        target
        for target in FLEET
        if in_slice(target, percent)
    ]


class TestTheSlice:
    def test_the_slice_is_deterministic(self):
        assert sliced(20) == sliced(20)

    def test_a_wider_slice_contains_the_narrower_one(self):
        assert set(sliced(10)) <= set(sliced(50))

    def test_the_full_slice_is_everyone(self):
        assert sliced(100) == FLEET

    def test_a_zero_slice_is_refused(self):
        with pytest.raises(Invalid):
            in_slice("x", 0)


def run_canary(new_digest_for):
    run = CanaryRun(percent=100)
    for target in FLEET[:10]:
        run.observe(target, "old", new_digest_for(target))
    return run


class TestVerdicts:
    def test_a_clean_canary_promotes_with_numbers(self):
        run = run_canary(lambda _target: "old")
        verdict = run.promotion_verdict()
        assert verdict.startswith(
            "PROMOTE: 10 built, agreement 100%, 0 failures"
        )

    def test_failures_are_not_a_percentage_question(self):
        run = run_canary(
            lambda target: None if target.endswith("3/lib") else "old"
        )
        verdict = run.promotion_verdict()
        assert verdict.startswith("HOLD: 1 failure(s) (pkg3/lib)")

    def test_low_agreement_names_the_differ_list(self):
        run = run_canary(
            lambda target: "NEW"
            if target in ("pkg1/lib", "pkg2/lib")
            else "old"
        )
        verdict = run.promotion_verdict()
        assert "agreement 80% under the 95% bar" in verdict
        assert "pkg1/lib, pkg2/lib" in verdict

    def test_a_tiny_slice_certifies_nothing(self):
        run = CanaryRun(percent=100)
        for target in FLEET[:3]:
            run.observe(target, "old", "old")
        assert "a tiny slice certifies nothing" in (
            run.promotion_verdict()
        )

    def test_an_empty_canary_cannot_report_agreement(self):
        with pytest.raises(Invalid):
            CanaryRun(percent=1).agreement()


class TestSkipping:
    def test_targets_outside_the_slice_are_counted_skipped(self):
        run = CanaryRun(percent=20)
        for target in FLEET:
            run.observe(target, "old", "old")
        assert run.built() + run.skipped == len(FLEET)
        assert run.skipped > 0
