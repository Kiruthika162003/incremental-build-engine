from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.firstbuild import FirstBuild


def newcomer() -> FirstBuild:
    return FirstBuild(developer="new-hire-asha")


class TestWalls:
    def test_each_wall_names_its_owner(self):
        verdict = newcomer().hit_wall(
            "missing-tool", "protoc assumed by the docs"
        )
        assert verdict == (
            "missing-tool: protoc assumed by the docs; the "
            "fix belongs to the scaffold"
        )

    def test_new_species_are_not_improvised(self):
        with pytest.raises(Invalid) as caught:
            newcomer().hit_wall("bad-vibes", "unclear")
        assert "not improvised" in str(caught.value)

    def test_walls_after_green_are_ordinary_bugs(self):
        chosen = newcomer()
        chosen.reach_green(minutes=25)
        with pytest.raises(Invalid) as caught:
            chosen.hit_wall("cold-cache", "late")
        assert "the first build is over" in str(caught.value)


class TestTheScorecard:
    def test_the_clean_first_build_is_an_introduction(self):
        chosen = newcomer()
        chosen.reach_green(minutes=12)
        assert chosen.scorecard() == (
            "new-hire-asha: green in 12 minute(s), zero "
            "walls; the platform introduced itself"
        )

    def test_walls_outweigh_minutes_and_say_so(self):
        chosen = newcomer()
        chosen.hit_wall("missing-tool", "protoc")
        chosen.hit_wall(
            "undocumented-env", "FORGE_REGION on one laptop"
        )
        chosen.reach_green(minutes=90)
        card = chosen.scorecard()
        assert "through 2 wall(s), and walls outweigh minutes" in (
            card
        )
        assert "a bus factor, not an onboarding" in card

    def test_the_scorecard_waits_for_green(self):
        with pytest.raises(Invalid) as caught:
            newcomer().scorecard()
        assert "the scorecard waits" in str(caught.value)
