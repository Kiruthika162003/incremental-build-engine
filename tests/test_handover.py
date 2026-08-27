from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.handover import Handover


def shift() -> Handover:
    built = Handover(outgoing="kiruthika")
    built.track(
        "INC-441", next_event="probe due at tick 60"
    )
    built.track(
        "breakglass-INC-441",
        next_event="grant expires at midnight",
    )
    return built


class TestTracking:
    def test_an_eventless_item_is_a_mood(self):
        with pytest.raises(Invalid) as caught:
            shift().track("mystery", next_event="  ")
        assert "a mood, not a calendar" in str(caught.value)

    def test_notes_about_finished_business_are_refused(self):
        chosen = shift()
        chosen.resolve("INC-441")
        with pytest.raises(Invalid) as caught:
            chosen.mention("INC-441", "it was fine")
        assert "belong in the chronicle" in str(caught.value)


class TestTheNote:
    def test_the_unmentioned_item_blocks_the_handover(self):
        chosen = shift()
        chosen.mention("INC-441", "breaker armed, retries calm")
        with pytest.raises(Invalid) as caught:
            chosen.note()
        assert "REFUSED: breakglass-INC-441" in str(caught.value)
        assert "a trap with a greeting" in str(caught.value)

    def test_the_full_note_is_a_calendar_with_a_name(self):
        chosen = shift()
        chosen.mention("INC-441", "breaker armed, retries calm")
        chosen.mention(
            "breakglass-INC-441", "one action taken, logged"
        )
        note = chosen.note()
        assert note.startswith("2 item(s) in flight:")
        assert (
            "INC-441: breaker armed, retries calm; next: "
            "probe due at tick 60"
        ) in note
        assert "you inherit a calendar, not a mood." in note
        assert "(kiruthika)" in note

    def test_the_genuinely_quiet_week_says_so_signed(self):
        chosen = shift()
        chosen.resolve("INC-441")
        chosen.resolve("breakglass-INC-441")
        assert chosen.note() == (
            "genuinely quiet; nothing in flight. (kiruthika)"
        )
