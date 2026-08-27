from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.mutants import Mutant, MutationRun, sample_plan

FLIP = Mutant(
    target_file="parser.c",
    description="flipped <= to <",
    mutant_id="m1",
)
DROP = Mutant(
    target_file="render.c",
    description="dropped the flush call",
    mutant_id="m2",
)
DEADZONE = Mutant(
    target_file="legacy.c",
    description="negated the guard",
    mutant_id="m3",
)


def run(killer_ids: set[str]) -> MutationRun:
    return MutationRun(
        suite_fails_on=lambda mutant_id: mutant_id in killer_ids
    )


class TestKillsAndSurvivors:
    def test_a_killed_mutant_credits_the_suite(self):
        chosen = run({"m1"})
        assert chosen.test_mutant(FLIP) == (
            "m1 killed; the suite works"
        )

    def test_the_survivor_is_a_shippable_bug_named(self):
        chosen = run(set())
        verdict = chosen.test_mutant(DROP)
        assert verdict == (
            "m2 SURVIVED: dropped the flush call in render.c "
            "would ship today"
        )

    def test_the_score_is_kills_over_mutants(self):
        chosen = run({"m1"})
        chosen.test_mutant(FLIP)
        chosen.test_mutant(DROP)
        assert chosen.score() == 0.5

    def test_no_mutants_no_score(self):
        with pytest.raises(Invalid):
            run(set()).score()


class TestTheReport:
    def test_the_report_spends_and_names(self):
        chosen = run({"m1"})
        chosen.test_mutant(FLIP)
        chosen.test_mutant(DROP)
        report = chosen.report()
        assert report.startswith(
            "1 of 2 mutant(s) killed (50%), 2 suite run(s) spent"
        )
        assert "hole: dropped the flush call in render.c" in (
            report
        )

    def test_dead_code_is_a_different_finding(self):
        chosen = run(set())
        chosen.test_mutant(DEADZONE)
        report = chosen.report(
            dead_code_files=frozenset({"legacy.c"})
        )
        assert "possibly dead code" in report
        assert "survived where nothing checks" in report


class TestTheBudget:
    def test_a_roomy_budget_exhausts(self):
        assert sample_plan(
            {"a.c": 3, "b.c": 4}, budget_runs=10
        ).startswith("run all 7 mutant(s)")

    def test_a_tight_budget_samples_and_says_so(self):
        plan = sample_plan(
            {"a.c": 30, "b.c": 40, "c.c": 20}, budget_runs=12
        )
        assert plan.startswith("sample 4 per file for 3 file(s)")
        assert "instead of implying exhaustion" in plan

    def test_no_budget_is_refused(self):
        with pytest.raises(Invalid):
            sample_plan({"a.c": 1}, budget_runs=0)
