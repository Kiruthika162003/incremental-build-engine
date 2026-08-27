from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.graph import Graph
from forge.packagecycles import PackageCycleAuditor


def tangled() -> PackageCycleAuditor:
    graph = Graph()
    graph.declare("billing/types")
    graph.declare("auth/helper", needs=("billing/types",))
    graph.declare("billing/charge", needs=("auth/session",))
    graph.declare("auth/session")
    graph.declare("search/index")
    return PackageCycleAuditor(graph=graph)


def clean() -> PackageCycleAuditor:
    graph = Graph()
    graph.declare("core/lib")
    graph.declare("app/main", needs=("core/lib",))
    return PackageCycleAuditor(graph=graph)


class TestDetection:
    def test_the_target_legal_package_cycle_is_found(self):
        report = tangled().audit()
        assert "1 package cycle(s)" in report
        assert "loop: auth, billing" in report

    def test_the_closing_edges_are_the_menu(self):
        report = tangled().audit()
        assert "auth/helper -> billing/types" in report
        assert "billing/charge -> auth/session" in report

    def test_a_clean_repo_can_leave_home(self):
        assert clean().audit() == (
            "no package cycles; every package can leave home"
        )

    def test_uninvolved_packages_stay_out_of_the_loop(self):
        assert "search" not in tangled().audit()


class TestTheRatchet:
    def test_a_falling_count_passes(self):
        auditor = tangled()
        auditor.audit()
        auditor.graph.targets["auth/helper"] = type(
            auditor.graph.targets["auth/helper"]
        )(name="auth/helper", needs=())
        assert "no package cycles" in auditor.audit()

    def test_a_rising_count_is_refused(self):
        auditor = clean()
        auditor.audit()
        auditor.graph.declare("core/back", needs=("app/main",))
        with pytest.raises(Invalid, match="only turns one way"):
            auditor.audit()

    def test_a_steady_count_passes(self):
        auditor = tangled()
        auditor.audit()
        assert "1 package cycle(s)" in auditor.audit()
