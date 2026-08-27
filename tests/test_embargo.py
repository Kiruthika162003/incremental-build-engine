from __future__ import annotations

import pytest

from forge.embargo import EmbargoRoom
from forge.errors import Invalid


def room() -> EmbargoRoom:
    built = EmbargoRoom(name="cve-2031-441", opened_at=100)
    built.build("compile:tlsfix", "fix-digest-1")
    built.build("link:patched-app", "fix-digest-2")
    return built


class TestTheRoom:
    def test_room_keys_are_salted_away_from_the_namespace(self):
        chosen = EmbargoRoom(name="cve-x", opened_at=0)
        verdict = chosen.build("compile:tlsfix", "d1")
        assert "built in the room under" in verdict
        assert verdict.split("under ")[1] != "compile:tlsfix"

    def test_building_after_the_lift_is_refused(self):
        chosen = room()
        chosen.lift(shared_cache={}, now=200)
        with pytest.raises(Invalid) as caught:
            chosen.build("compile:more", "d9")
        assert "a new embargo, not a footnote" in str(caught.value)


class TestTheLeakCheck:
    def test_a_quiet_shared_cache_reads_clean(self):
        verdict = room().leak_check(
            {"compile:other": "unrelated-digest"}
        )
        assert verdict.startswith("clean: 2 private entrie(s)")

    def test_the_leak_is_an_incident_not_a_warning(self):
        verdict = room().leak_check(
            {"compile:something": "fix-digest-1"}
        )
        assert verdict.startswith("INCIDENT: compile:tlsfix")
        assert "disclosure, whatever the intent" in verdict


class TestTheLift:
    def test_the_lift_republishes_and_empties_the_room(self):
        chosen = room()
        chosen.leak_check({})
        shared: dict[str, str] = {}
        verdict = chosen.lift(shared, now=350)
        assert verdict.startswith(
            "cve-2031-441 lifted: 2 entrie(s) republished "
            "unsalted after 250 tick(s) private"
        )
        assert "1 clean leak check(s) on record" in verdict
        assert shared["compile:tlsfix"] == "fix-digest-1"
        assert chosen.private_entries == {}

    def test_lifting_twice_is_refused(self):
        chosen = room()
        chosen.lift({}, now=200)
        with pytest.raises(Invalid):
            chosen.lift({}, now=300)

    def test_time_travel_is_refused(self):
        with pytest.raises(Invalid):
            room().lift({}, now=50)
