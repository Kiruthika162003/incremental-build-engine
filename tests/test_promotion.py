from __future__ import annotations

import pytest

from forge.errors import Invalid, Missing
from forge.promotion import Ladder

DIGEST = "feedface0011"


def entered() -> Ladder:
    ladder = Ladder()
    ladder.enter("app-3.1", DIGEST)
    return ladder


class TestTheClimb:
    def test_the_artifact_climbs_one_rung_at_a_time(self):
        ladder = entered()
        assert ladder.promote("app-3.1", DIGEST) == (
            "app-3.1 is on staging, same bytes"
        )
        assert ladder.where("app-3.1") == "staging"

    def test_the_top_rung_has_nothing_above(self):
        ladder = entered()
        for _ in range(3):
            ladder.promote("app-3.1", DIGEST)
        assert ladder.where("app-3.1") == "production"
        with pytest.raises(Invalid):
            ladder.promote("app-3.1", DIGEST)

    def test_reentry_is_refused(self):
        ladder = entered()
        with pytest.raises(Invalid):
            ladder.enter("app-3.1", "other")


class TestIdentity:
    def test_a_rebuilt_binary_is_caught_at_the_gate(self):
        ladder = entered()
        with pytest.raises(Invalid) as caught:
            ladder.promote("app-3.1", "abcdef990022")
        assert "someone rebuilt instead of promoting" in str(
            caught.value
        )

    def test_a_stranger_cannot_promote(self):
        with pytest.raises(Missing):
            entered().promote("ghost", DIGEST)


class TestDemotion:
    def test_a_rollback_carries_its_reason(self):
        ladder = entered()
        ladder.promote("app-3.1", DIGEST)
        verdict = ladder.demote(
            "app-3.1", DIGEST, "p99 regression on canary dash"
        )
        assert verdict == (
            "app-3.1 rolled back to dev: p99 regression on "
            "canary dash"
        )

    def test_a_reasonless_rollback_is_refused(self):
        ladder = entered()
        ladder.promote("app-3.1", DIGEST)
        with pytest.raises(Invalid):
            ladder.demote("app-3.1", DIGEST, "   ")

    def test_the_bottom_rung_cannot_demote(self):
        with pytest.raises(Invalid):
            entered().demote("app-3.1", DIGEST, "why not")


class TestTheStory:
    def test_the_story_is_a_straight_line_of_rungs(self):
        ladder = entered()
        ladder.promote("app-3.1", DIGEST)
        ladder.promote("app-3.1", DIGEST)
        ladder.demote("app-3.1", DIGEST, "error budget spent")
        story = ladder.story("app-3.1").splitlines()
        assert story[0] == "app-3.1 entered dev (feedface)"
        assert story[1] == "app-3.1 promoted dev -> staging"
        assert story[3] == (
            "app-3.1 demoted canary -> staging: error budget spent"
        )

    def test_a_story_needs_a_subject(self):
        with pytest.raises(Missing):
            entered().story("ghost")
