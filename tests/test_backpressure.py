from __future__ import annotations

import pytest

from forge.backpressure import BoundedQueue
from forge.errors import Invalid


def queue() -> BoundedQueue:
    return BoundedQueue(capacity=10, drain_per_tick=2)


class TestAdmission:
    def test_a_calm_offer_is_admitted_quietly(self):
        assert queue().offer(4) == "4 admitted quietly"

    def test_the_full_queue_refuses_at_the_door(self):
        chosen = queue()
        chosen.offer(8)
        verdict = chosen.offer(6)
        assert "2 admitted, 4 refused at the door" in verdict
        assert "depth 10/10, draining 2/tick" in verdict
        assert "roughly 5 tick(s) to clear" in verdict
        assert "a blip or a collapse" in verdict

    def test_draining_reopens_the_door(self):
        chosen = queue()
        chosen.offer(10)
        chosen.drain_tick()
        chosen.drain_tick()
        assert chosen.offer(4) == "4 admitted quietly"

    def test_walls_and_pipes_are_refused(self):
        with pytest.raises(Invalid):
            BoundedQueue(capacity=0, drain_per_tick=1)
        with pytest.raises(Invalid):
            BoundedQueue(capacity=5, drain_per_tick=0)

    def test_offering_nothing_is_refused(self):
        with pytest.raises(Invalid):
            queue().offer(0)


class TestTheLedger:
    def test_the_swallowed_debt_is_named(self):
        chosen = queue()
        chosen.offer(8)
        chosen.offer(6)
        chosen.offer(3)
        ledger = chosen.ledger()
        assert "10 admitted, 7 refused instantly" in ledger
        assert "would have swallowed 7" in ledger
        assert "whoever stood nearest" in ledger
