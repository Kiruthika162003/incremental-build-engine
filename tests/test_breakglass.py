from __future__ import annotations

import pytest

from forge.breakglass import BreakGlass
from forge.errors import Invalid


def grant() -> BreakGlass:
    return BreakGlass(
        incident="cache outage INC-441",
        human="kiruthika",
        opened_at=100,
        expires_at=160,
    )


class TestOpening:
    def test_the_glass_needs_a_name_and_an_incident(self):
        with pytest.raises(Invalid):
            BreakGlass(
                incident=" ",
                human="dev",
                opened_at=0,
                expires_at=10,
            )

    def test_the_grant_must_expire_after_it_opens(self):
        with pytest.raises(Invalid):
            BreakGlass(
                incident="x",
                human="dev",
                opened_at=10,
                expires_at=10,
            )


class TestActing:
    def test_actions_land_in_the_testimony(self):
        chosen = grant()
        entry = chosen.act("flushed the poisoned entry", now=110)
        assert entry == (
            "[110] kiruthika: flushed the poisoned entry"
        )

    def test_the_door_does_not_stay_propped(self):
        chosen = grant()
        with pytest.raises(Invalid) as caught:
            chosen.act("late poke", now=160)
        assert "does not stay propped" in str(caught.value)

    def test_a_closed_grant_refuses_new_habits(self):
        chosen = grant()
        chosen.close(now=130)
        with pytest.raises(Invalid) as caught:
            chosen.act("one more thing", now=131)
        assert "a new incident, not a habit" in str(caught.value)


class TestClosingAndTestimony:
    def test_early_closure_is_rewarded_in_the_record(self):
        verdict = grant().close(now=140)
        assert verdict == (
            "closed 20 tick(s) early; the record rewards doors "
            "that shut before they must"
        )

    def test_the_testimony_reads_whole(self):
        chosen = grant()
        chosen.act("rotated the lease", now=105)
        chosen.close(now=120)
        testimony = chosen.testimony()
        assert testimony.startswith(
            "cache outage INC-441 (kiruthika), opened 100, "
            "closed at 120, 1 privileged action(s)"
        )
        assert "[105] kiruthika: rotated the lease" in testimony
        assert "how long it stays open" in testimony
