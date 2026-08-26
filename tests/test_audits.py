from __future__ import annotations

import importlib

import pytest

from forge.audits.finding import Finding
from forge.audits.registry import AUDITS, all_findings, broken, report


class TestFindings:
    def test_the_line_carries_the_mark_and_numbers(self):
        finding = Finding(
            audit="sample", claim="two is two", numbers={"two": 2}
        )
        assert finding.line() == "sample: two is two [holds] (two=2)"

    def test_a_broken_finding_says_so(self):
        finding = Finding(
            audit="sample", claim="wishful", numbers={}, holds=False
        )
        assert "[BROKEN]" in finding.line()


@pytest.mark.parametrize("dotted", AUDITS)
class TestEveryAudit:
    def test_the_audit_holds(self, dotted):
        module = importlib.import_module(dotted)
        finding = module.run()
        assert finding.holds, finding.line()

    def test_the_audit_answers_to_its_name(self, dotted):
        module = importlib.import_module(dotted)
        assert module.run().audit == dotted.rsplit(".", 1)[1]

    def test_every_finding_carries_numbers(self, dotted):
        module = importlib.import_module(dotted)
        assert module.run().numbers


class TestTheRegistry:
    def test_nothing_is_broken(self):
        assert broken() == []

    def test_no_audit_registers_twice(self):
        assert len(AUDITS) == len(set(AUDITS))

    def test_the_report_renders_every_line(self):
        page = report()
        assert page.count(": ") >= len(all_findings())
        assert page.endswith(f"{len(AUDITS)} audits, 0 broken")
