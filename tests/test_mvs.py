from __future__ import annotations

import pytest

from forge.errors import Invalid, Missing
from forge.mvs import Universe


def diamond() -> Universe:
    universe = Universe()
    universe.declare(
        "app", requires={"web": (1, 0), "storage": (1, 0)}
    )
    universe.declare("web", requires={"json": (1, 2)})
    universe.declare("storage", requires={"json": (1, 4)})
    universe.declare("json")
    return universe


class TestSelection:
    def test_the_diamond_takes_the_maximum_of_minimums(self):
        selection = diamond().select("app")
        assert selection["json"] == (1, 4)

    def test_the_answer_has_no_registry_in_it(self):
        first = diamond().select("app")
        second = diamond().select("app")
        assert first == second

    def test_missing_modules_are_named_with_their_wanter(self):
        universe = diamond()
        universe.modules["web"].requires["ghost"] = (1, 0)
        with pytest.raises(Missing, match="web requires ghost"):
            universe.select("app")

    def test_an_unknown_root_is_refused(self):
        with pytest.raises(Missing):
            diamond().select("nothing")

    def test_double_declaration_is_refused(self):
        universe = diamond()
        with pytest.raises(Invalid):
            universe.declare("json")


class TestBlame:
    def test_the_forcing_requirement_is_a_lookup_not_a_hunt(self):
        assert diamond().blame("app", "json") == (
            "json (1, 4) was forced by storage; every other "
            "requirement wanted the same or older"
        )

    def test_blaming_the_unselected_is_refused(self):
        universe = diamond()
        universe.declare("unused")
        with pytest.raises(Missing):
            universe.blame("app", "unused")


class TestUpgrades:
    def test_the_selection_moves_only_when_someone_edits(self):
        moved = diamond().upgrade_delta(
            "app", "web", "json", (1, 6)
        )
        assert moved == ["json: (1, 4) -> (1, 6)"]

    def test_an_absorbed_edit_says_so(self):
        moved = diamond().upgrade_delta(
            "app", "web", "json", (1, 3)
        )
        assert moved == ["nothing moves; the edit is absorbed"]

    def test_the_probe_leaves_the_universe_untouched(self):
        universe = diamond()
        universe.upgrade_delta("app", "web", "json", (1, 6))
        assert universe.modules["web"].requires["json"] == (1, 2)

    def test_editing_a_requirement_that_never_was_is_refused(self):
        with pytest.raises(Invalid):
            diamond().upgrade_delta("app", "json", "web", (2, 0))
