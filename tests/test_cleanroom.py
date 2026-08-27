from __future__ import annotations

import pytest

from forge.cleanroom import CleanRoom
from forge.errors import Invalid

CLEAN = {"parser.o": "c1", "lexer.o": "c2", "app": "c3"}


class TestTheComparison:
    def test_a_clean_night_renews_trust(self):
        room = CleanRoom()
        report = room.compare(dict(CLEAN), dict(CLEAN))
        assert report.startswith(
            "3 agreement(s), 0 contradiction(s), 0 drift"
        )

    def test_the_contradiction_names_entry_and_response(self):
        room = CleanRoom()
        incremental = dict(CLEAN, **{"parser.o": "STALE"})
        report = room.compare(incremental, dict(CLEAN))
        assert "1 contradiction(s)" in report
        assert (
            "parser.o: incremental STALE against clean c1; "
            "invalidate the entry and its cone"
        ) in report

    def test_drift_is_reported_from_both_sides(self):
        room = CleanRoom()
        incremental = dict(CLEAN, **{"ghost.o": "g"})
        clean = dict(CLEAN, **{"newborn.o": "n"})
        report = room.compare(incremental, clean)
        assert "2 drift" in report
        assert "ghost.o exists only incrementally" in report
        assert "newborn.o exists only in the clean world" in report

    def test_a_silent_clean_build_is_an_outage(self):
        with pytest.raises(Invalid):
            CleanRoom().compare(dict(CLEAN), {})


class TestTheTrustVerdict:
    def test_clean_nights_renew_trust(self):
        room = CleanRoom()
        for _ in range(3):
            room.compare(dict(CLEAN), dict(CLEAN))
        assert room.trust_verdict().startswith("trust renewed")

    def test_one_dirty_night_is_maintenance(self):
        room = CleanRoom()
        room.compare(dict(CLEAN), dict(CLEAN))
        room.compare(
            dict(CLEAN, **{"parser.o": "STALE"}), dict(CLEAN)
        )
        verdict = room.trust_verdict()
        assert verdict.startswith("maintenance")
        assert "invalidate and watch" in verdict

    def test_three_dirty_nights_accuse_the_engine(self):
        room = CleanRoom()
        for _ in range(3):
            room.compare(
                dict(CLEAN, **{"parser.o": "STALE"}),
                dict(CLEAN),
            )
        assert room.trust_verdict().startswith("ENGINE BUG")

    def test_no_nights_cannot_be_judged(self):
        with pytest.raises(Invalid):
            CleanRoom().trust_verdict()
