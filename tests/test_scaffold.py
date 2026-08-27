from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.scaffold import RepoState, grade, production_gate, report


def repo(*present: str) -> RepoState:
    return RepoState(
        name="new-service", present=frozenset(present)
    )


FULL = repo(
    "build_file", "owners_record", "test_directory", "ci_hook"
)


class TestGrading:
    def test_the_complete_repo_earns_an_a(self):
        letter, gaps = grade(FULL)
        assert (letter, gaps) == ("A", [])

    def test_each_gap_costs_a_letter(self):
        letter, _ = grade(repo("build_file", "ci_hook"))
        assert letter == "C"
        assert grade(repo())[0] == "F"

    def test_the_gap_carries_its_why_and_its_price(self):
        _, gaps = grade(repo("build_file", "ci_hook", "test_directory"))
        assert len(gaps) == 1
        assert gaps[0].startswith(
            "owners_record: unowned code is orphaned"
        )
        assert "archaeology project" in gaps[0]

    def test_unknown_pieces_are_refused(self):
        with pytest.raises(Invalid):
            grade(repo("build_file", "vibes_folder"))


class TestTheReport:
    def test_the_report_is_public_and_specific(self):
        page = report(repo("build_file"))
        assert page.startswith("new-service: grade D (1 of 4)")
        assert "missing ci_hook: unhooked repos rot green" in page


class TestTheGate:
    def test_a_and_b_repos_may_ship(self):
        assert "may take production traffic at grade A" in (
            production_gate(FULL)
        )

    def test_the_incomplete_repo_is_blocked_with_economics(self):
        with pytest.raises(Invalid) as caught:
            production_gate(repo("build_file"))
        assert "production is not the place to discover" in (
            str(caught.value)
        )
        assert "grading is cheap and the incident is not" in (
            str(caught.value)
        )
