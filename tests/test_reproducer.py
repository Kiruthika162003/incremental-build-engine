from __future__ import annotations

import pytest

from forge.errors import Invalid, Missing
from forge.reproducer import ReproBundle

FACTS = {
    "seal_fingerprint": "aabbccdd",
    "action_key": "compile:parser|inputs=1122",
    "command": "cc -O2 parser.c",
    "input_digests": "parser.c=3344,parser.h=5566",
    "replay_coordinates": "log=run-88,step=41",
}


def bundle() -> ReproBundle:
    return ReproBundle(facts=dict(FACTS))


class TestTheBundle:
    def test_a_complete_bundle_attaches_cleanly(self):
        page = bundle().ticket_attachment()
        assert page.startswith(
            "repro bundle, mechanically complete:"
        )
        assert "  command: cc -O2 parser.c" in page

    def test_holes_are_refused_with_their_names(self):
        broken = dict(FACTS, input_digests=" ")
        with pytest.raises(Invalid) as caught:
            ReproBundle(facts=broken)
        assert "the bundle has holes: input_digests" in str(
            caught.value
        )
        assert "back to an argument" in str(caught.value)


class TestTheCheck:
    def test_a_faithful_attempt_matches_every_ingredient(self):
        verdict = bundle().check_against(dict(FACTS))
        assert verdict.startswith("every ingredient matches")
        assert "a bug against the format" in verdict

    def test_the_first_differing_ingredient_is_a_coordinate(self):
        attempt = dict(FACTS, command="cc -O0 parser.c")
        verdict = bundle().check_against(attempt)
        assert verdict.startswith(
            "differs at ingredient 3 (command)"
        )
        assert "became a coordinate" in verdict

    def test_an_attempt_that_recorded_nothing_is_missing(self):
        attempt = dict(FACTS)
        del attempt["replay_coordinates"]
        with pytest.raises(Missing):
            bundle().check_against(attempt)
