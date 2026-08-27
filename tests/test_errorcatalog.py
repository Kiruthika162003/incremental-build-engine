from __future__ import annotations

import pytest

from forge.errorcatalog import Diagnostic, ErrorCatalog
from forge.errors import Invalid


def catalog() -> ErrorCatalog:
    built = ErrorCatalog()
    built.register(
        Diagnostic(
            code="F001",
            explanation="undeclared read",
            fixit="add the path to reads",
        )
    )
    built.register(
        Diagnostic(
            code="F002",
            explanation="cycle in the graph",
        )
    )
    return built


class TestTheCatalog:
    def test_emissions_carry_code_explanation_and_fix(self):
        line = catalog().emit("F001", "main.o read secret.h")
        assert line == (
            "[F001] undeclared read: main.o read secret.h "
            "(fix: add the path to reads)"
        )

    def test_fixless_diagnostics_emit_without_a_fix_line(self):
        line = catalog().emit("F002", "a -> b -> a")
        assert "(fix:" not in line

    def test_uncatalogued_codes_are_refused(self):
        with pytest.raises(Invalid, match="free text"):
            catalog().emit("F999", "mystery")

    def test_explanationless_codes_are_refused(self):
        with pytest.raises(Invalid, match="trench coat"):
            ErrorCatalog().register(
                Diagnostic(code="F003", explanation="  ")
            )

    def test_double_registration_is_refused(self):
        built = catalog()
        with pytest.raises(Invalid):
            built.register(
                Diagnostic(code="F001", explanation="again")
            )


class TestTheReport:
    def test_confusion_ranks_by_frequency(self):
        built = catalog()
        for _ in range(3):
            built.emit("F002", "loop")
        built.emit("F001", "leak")
        report = built.weekly_report()
        lines = report.splitlines()
        assert lines[0].startswith("F002: 3 emissions")
        assert "[no mechanical fix; a rewrite candidate]" in lines[0]

    def test_fixit_coverage_is_the_score(self):
        built = catalog()
        built.emit("F001", "leak")
        built.emit("F002", "loop")
        assert "fix-it coverage: 1/2" in built.weekly_report()
        assert "(50%)" in built.weekly_report()

    def test_the_rewrite_candidate_is_the_frequent_fixless(self):
        built = catalog()
        for _ in range(400):
            built.emit("F002", "loop")
        built.emit("F001", "leak")
        assert built.rewrite_candidate() == (
            "F002 bit 400 times with no mechanical fix; rewrite "
            "this one first"
        )

    def test_a_fully_fixed_week_has_no_candidate(self):
        built = catalog()
        built.emit("F001", "leak")
        assert built.rewrite_candidate() is None

    def test_a_quiet_week_says_so(self):
        assert catalog().weekly_report().startswith("no errors emitted")
