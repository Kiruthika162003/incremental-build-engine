from __future__ import annotations

import pytest

from forge.errors import Invalid, Missing
from forge.localoverride import OverrideBook


def book() -> OverrideBook:
    built = OverrideBook(locked={"json": "2.1", "zlib": "1.3"})
    built.override("json", "/home/dev/json-checkout", now=0)
    return built


class TestResolution:
    def test_the_override_wins_while_it_stands(self):
        assert book().resolve("json") == "/home/dev/json-checkout"

    def test_the_lock_answers_for_everything_else(self):
        assert book().resolve("zlib") == "registry:zlib@1.3"

    def test_overriding_the_unlocked_is_refused(self):
        with pytest.raises(Missing, match="nothing to override"):
            book().override("mystery", "/tmp/x", now=0)

    def test_double_overriding_is_refused(self):
        built = book()
        with pytest.raises(Invalid):
            built.override("json", "/elsewhere", now=1)


class TestTheTaint:
    def test_building_with_an_override_wears_the_taint(self):
        built = book()
        verdict = built.built("app", used={"json", "zlib"})
        assert verdict == "app built TAINTED by json"

    def test_clean_builds_stay_clean(self):
        built = book()
        assert built.built("tool", used={"zlib"}) == (
            "tool built clean"
        )

    def test_tainted_artifacts_refuse_release_flat(self):
        built = book()
        built.built("app", used={"json"})
        refusal = built.may_release("app")
        assert refusal.startswith("REFUSED: app embeds")
        assert "no lock or reviewer ever saw" in refusal

    def test_clean_artifacts_may_ship(self):
        built = book()
        built.built("tool", used={"zlib"})
        assert built.may_release("tool") == "tool may ship"


class TestTheExit:
    def test_dropping_lists_the_rebuild_debt(self):
        built = book()
        built.built("app", used={"json"})
        verdict = built.drop("json")
        assert "rebuild app before the workspace tells the truth" in (
            verdict
        )

    def test_the_rebuilt_artifact_ships_after_the_drop(self):
        built = book()
        built.built("app", used={"json"})
        built.drop("json")
        assert built.may_release("app") == "app may ship"

    def test_an_unused_override_drops_quietly(self):
        built = book()
        assert built.drop("json") == (
            "override dropped; nothing was built under it"
        )

    def test_the_ancient_override_is_named_a_fork(self):
        built = book()
        report = built.standing_report(now=150)
        assert "150 ticks standing" in report
        assert "a fork wearing a bookmark's clothes" in report
