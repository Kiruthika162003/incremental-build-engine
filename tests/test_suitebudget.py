from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.suitebudget import DirectoryBudget, suite_report


def parser_dir() -> DirectoryBudget:
    budget = DirectoryBudget(
        directory="tests/parser",
        allowance_ms=500,
        per_test_norm_ms=100,
    )
    budget.admit("test_tokens", 40)
    budget.admit("test_tree", 60)
    return budget


class TestAdmission:
    def test_a_normal_test_admits_quietly(self):
        assert parser_dir().admit("test_more", 80) == (
            "test_more admitted at 80ms"
        )

    def test_a_slow_test_without_a_waiver_is_refused(self):
        budget = parser_dir()
        with pytest.raises(Invalid) as caught:
            budget.admit("test_fuzz", 400)
        assert "slow is admissible, shrugging is not" in str(
            caught.value
        )

    def test_a_slow_test_with_a_waiver_is_admitted(self):
        budget = parser_dir()
        budget.admit(
            "test_fuzz",
            400,
            waiver="exhaustive grammar corpus, sharded weekly",
        )
        assert budget.tests["test_fuzz"] == 400

    def test_double_admission_is_refused(self):
        budget = parser_dir()
        with pytest.raises(Invalid):
            budget.admit("test_tokens", 40)


class TestReports:
    def test_a_healthy_directory_shows_headroom(self):
        assert parser_dir().report().startswith(
            "tests/parser: 100ms of 500ms (400ms headroom)"
        )

    def test_the_overdraft_names_the_cheapest_path_back(self):
        budget = parser_dir()
        budget.admit("test_fuzz", 450, waiver="corpus sweep")
        report = budget.report()
        assert "OVERDRAFT 50ms" in report
        assert (
            "speed up or shard test_fuzz (450ms)" in report
        )

    def test_waivers_print_with_the_report(self):
        budget = parser_dir()
        budget.admit("test_fuzz", 200, waiver="corpus sweep")
        assert "waiver: test_fuzz: corpus sweep" in budget.report()

    def test_the_suite_sorts_the_worst_directory_first(self):
        deep = DirectoryBudget(
            directory="tests/integration",
            allowance_ms=100,
            per_test_norm_ms=100,
        )
        deep.admit("test_end_to_end", 90)
        deep.admit("test_smoke", 60)
        report = suite_report([parser_dir(), deep])
        lines = report.splitlines()
        assert lines[0] == "2 directories, 1 in overdraft"
        assert lines[1].startswith("tests/integration: OVERDRAFT")

    def test_an_empty_suite_is_refused(self):
        with pytest.raises(Invalid):
            suite_report([])
