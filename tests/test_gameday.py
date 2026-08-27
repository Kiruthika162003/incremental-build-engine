from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.gameday import GameDay


def planned() -> GameDay:
    day = GameDay()
    day.expect("kill-worker-7", "retry")
    day.expect("poison-cache-entry", "prover")
    day.expect("flood-the-queue", "breaker")
    return day


class TestDeclarations:
    def test_late_expectations_are_called_observations(self):
        day = planned()
        day.inject("kill-worker-7", handled_by="retry")
        with pytest.raises(Invalid) as caught:
            day.expect("new-fault", "hope")
        assert "called observations" in str(caught.value)

    def test_surprise_faults_belong_in_incidents(self):
        with pytest.raises(Invalid) as caught:
            planned().inject("meteor", handled_by=None)
        assert "belong in incidents, not exercises" in str(
            caught.value
        )


class TestTheThreeOutcomes:
    def test_the_held_claim_is_credited(self):
        assert planned().inject(
            "kill-worker-7", handled_by="retry"
        ) == "kill-worker-7: held by retry as claimed"

    def test_nothing_catching_it_is_a_plain_failure(self):
        verdict = planned().inject(
            "poison-cache-entry", handled_by=None
        )
        assert "FAILED, nothing caught it" in verdict

    def test_the_wrong_mechanism_is_the_instructive_one(self):
        verdict = planned().inject(
            "flood-the-queue", handled_by="retry"
        )
        assert "absorbed by retry where breaker claimed it" in (
            verdict
        )
        assert "hiding a misconfiguration" in verdict


class TestTheScorecard:
    def test_the_mixed_day_grades_every_fault(self):
        day = planned()
        day.inject("kill-worker-7", handled_by="retry")
        day.inject("poison-cache-entry", handled_by=None)
        day.inject("flood-the-queue", handled_by="retry")
        card = day.scorecard()
        assert card.startswith(
            "1 held, 1 failed, 1 handled by the wrong mechanism"
        )
        assert "failed: poison-cache-entry" in card
        assert (
            "misrouted: flood-the-queue (by retry, not breaker)"
        ) in card

    def test_the_perfect_score_is_rerun_harder(self):
        day = planned()
        day.inject("kill-worker-7", handled_by="retry")
        day.inject("poison-cache-entry", handled_by="prover")
        day.inject("flood-the-queue", handled_by="breaker")
        assert "rerun harder" in day.scorecard()
        assert "the drill was soft, not the platform hard" in (
            day.scorecard()
        )

    def test_an_unrun_day_has_no_card(self):
        with pytest.raises(Invalid):
            planned().scorecard()
