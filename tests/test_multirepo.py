from __future__ import annotations

import pytest

from forge.errors import Invalid, Missing
from forge.multirepo import PinBook, SiblingRepo


def world() -> PinBook:
    book = PinBook()
    protolib = SiblingRepo(name="protolib")
    for commit in ("p1", "p2", "p3", "p4"):
        protolib.land(commit)
    idle = SiblingRepo(name="idlerepo")
    idle.land("i1")
    book.track(protolib)
    book.track(idle)
    book.pin("protolib", "p2", now=0)
    book.pin("idlerepo", "i1", now=0)
    return book


class TestPinning:
    def test_a_pin_names_an_exact_commit(self):
        book = world()
        assert book.pins["protolib"][0] == "p2"

    def test_pinning_a_ghost_commit_is_refused(self):
        book = world()
        with pytest.raises(Missing, match="points at nothing"):
            book.pin("protolib", "p99", now=1)

    def test_unknown_siblings_are_refused(self):
        with pytest.raises(Missing):
            world().pin("mystery", "x", now=0)

    def test_double_tracking_is_refused(self):
        book = world()
        with pytest.raises(Invalid):
            book.track(SiblingRepo(name="protolib"))


class TestUpdates:
    def test_the_proposal_names_every_crossed_commit(self):
        proposal = world().propose_update("protolib")
        assert proposal == (
            "moving protolib from p2 to p4 crosses 2 commits: p3, p4"
        )

    def test_a_pin_at_head_has_nothing_to_adopt(self):
        book = world()
        book.adopt("protolib", now=5)
        assert book.propose_update("protolib") == (
            "protolib is at head; nothing to adopt"
        )


class TestAging:
    def test_staleness_is_measured_in_commits_not_days(self):
        report = world().age_report()
        assert "protolib at p2: trails head by 2 commits" in report
        assert "idlerepo at i1: trails head by 0 commits" in report

    def test_the_worst_trailing_pin_leads_and_is_advised(self):
        report = world().age_report()
        lines = report.splitlines()
        assert lines[0].startswith("protolib")
        assert lines[-1] == (
            "catch up protolib first; that is where the conflicts "
            "are compounding"
        )

    def test_an_all_current_book_gives_no_advice(self):
        book = world()
        book.adopt("protolib", now=5)
        assert "catch up" not in book.age_report()

    def test_an_empty_book_is_refused(self):
        with pytest.raises(Invalid):
            PinBook().age_report()
