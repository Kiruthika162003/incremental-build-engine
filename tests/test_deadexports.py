from __future__ import annotations

import pytest

from forge.deadexports import ExportCensus
from forge.errors import Invalid


def census() -> ExportCensus:
    built = ExportCensus()
    built.declare_unit(
        "corelib",
        exports=("parse", "render", "legacy_walk"),
        dependent_count=6,
    )
    built.declare_unit(
        "app",
        exports=("main",),
        imports=(("corelib", "parse"), ("corelib", "render")),
    )
    return built


class TestTheCensus:
    def test_the_dead_export_names_its_cone(self):
        findings = census().dead()
        assert len(findings) == 2
        assert (
            "corelib.legacy_walk: no consumer; make it private "
            "and stop dragging 6 dependent(s) when it moves"
        ) in findings

    def test_consumed_exports_are_not_accused(self):
        assert not any(
            "parse" in finding for finding in census().dead()
        )

    def test_main_is_dead_until_exempted(self):
        chosen = census()
        assert any(
            "app.main" in finding for finding in chosen.dead()
        )
        chosen.exempt(
            "app", "main", reason="process entry point"
        )
        assert not any(
            "app.main" in finding for finding in chosen.dead()
        )

    def test_an_exemption_without_a_reason_is_refused(self):
        with pytest.raises(Invalid) as caught:
            census().exempt("app", "main", reason="  ")
        assert "write the reason" in str(caught.value)

    def test_double_declaration_is_refused(self):
        chosen = census()
        with pytest.raises(Invalid):
            chosen.declare_unit("app", exports=())


class TestTheReport:
    def test_the_report_carries_findings_and_exemptions(self):
        chosen = census()
        chosen.exempt("app", "main", reason="process entry point")
        report = chosen.report()
        assert report.startswith("1 dead export(s)")
        assert "corelib.legacy_walk" in report
        assert "exempt app.main: process entry point" in report

    def test_a_clean_census_says_so(self):
        chosen = census()
        chosen.exempt("app", "main", reason="entry point")
        chosen.declare_unit(
            "tool",
            exports=(),
            imports=(("corelib", "legacy_walk"),),
        )
        assert chosen.report().startswith(
            "every export has a consumer or a reason"
        )
