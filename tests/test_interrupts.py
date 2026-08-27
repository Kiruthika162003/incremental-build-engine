from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.interrupts import GRACE_TICKS, CancelController

ACTIONS = ["a.o", "b.o", "c.o", "d.o"]


def midflight() -> CancelController:
    controller = CancelController(total_actions=list(ACTIONS))
    controller.start("a.o", now=0, takes=2)
    controller.start("b.o", now=0, takes=3)
    controller.start("c.o", now=0, takes=20)
    controller.tick(now=2)
    return controller


class TestTheProtocol:
    def test_completed_work_is_banked_before_the_cancel(self):
        controller = midflight()
        assert controller.completed == ["a.o"]

    def test_cancel_stops_new_starts_immediately(self):
        controller = midflight()
        controller.cancel(now=2)
        assert controller.start("d.o", now=2, takes=1) == (
            "refused: the build is cancelling"
        )

    def test_the_grace_window_lets_the_nearly_done_finish(self):
        controller = midflight()
        controller.cancel(now=2)
        controller.tick(now=3)
        assert "b.o" in controller.completed
        assert controller.killed == []

    def test_the_grace_expires_and_the_stubborn_are_killed(self):
        controller = midflight()
        controller.cancel(now=2)
        controller.tick(now=2 + GRACE_TICKS)
        assert controller.killed == ["c.o"]
        assert controller.running == []

    def test_double_cancel_is_refused(self):
        controller = midflight()
        controller.cancel(now=2)
        with pytest.raises(Invalid):
            controller.cancel(now=3)

    def test_strangers_cannot_start(self):
        with pytest.raises(Invalid):
            midflight().start("ghost.o", now=0, takes=1)


class TestTheResume:
    def test_the_receipt_predicts_the_next_build(self):
        controller = midflight()
        controller.cancel(now=2)
        controller.tick(now=2 + GRACE_TICKS)
        assert controller.receipt() == (
            "2 completed and cache-warm, 1 killed and honestly "
            "absent, 1 never started; the next build owes 2 actions"
        )

    def test_the_owed_list_is_killed_plus_never_started(self):
        controller = midflight()
        controller.cancel(now=2)
        controller.tick(now=2 + GRACE_TICKS)
        assert controller.next_build_owes() == ["c.o", "d.o"]

    def test_a_cancel_before_anything_ran_owes_everything(self):
        controller = CancelController(total_actions=list(ACTIONS))
        controller.cancel(now=0)
        controller.tick(now=GRACE_TICKS)
        assert controller.next_build_owes() == sorted(ACTIONS)
