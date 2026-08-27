from __future__ import annotations

import pytest

from forge.buildqueue import FarmQueue, QueuedBuild
from forge.errors import Invalid


def full_farm() -> FarmQueue:
    queue = FarmQueue(slots=2)
    queue.submit(QueuedBuild(name="batch-a", kind="batch", arrived=0))
    queue.submit(QueuedBuild(name="batch-b", kind="batch", arrived=1))
    return queue


class TestAdmission:
    def test_free_slots_run_immediately(self):
        queue = FarmQueue(slots=1)
        outcome = queue.submit(
            QueuedBuild(name="dev", kind="interactive", arrived=0)
        )
        assert outcome == "running"

    def test_one_waiting_human_does_not_preempt(self):
        queue = full_farm()
        outcome = queue.submit(
            QueuedBuild(name="dev1", kind="interactive", arrived=2)
        )
        assert outcome == "waiting"
        assert queue.preemptions == 0

    def test_the_second_waiting_human_triggers_the_preemption(self):
        queue = full_farm()
        queue.submit(
            QueuedBuild(name="dev1", kind="interactive", arrived=2)
        )
        outcome = queue.submit(
            QueuedBuild(name="dev2", kind="interactive", arrived=3)
        )
        assert outcome == "running after preempting batch-b"
        assert queue.work_ticks_lost == 5

    def test_bad_kinds_and_empty_farms_are_refused(self):
        with pytest.raises(Invalid):
            QueuedBuild(name="x", kind="cosmic", arrived=0)
        with pytest.raises(Invalid):
            FarmQueue(slots=0)


class TestOrdering:
    def test_humans_queue_among_themselves_by_arrival(self):
        queue = FarmQueue(slots=2)
        queue.submit(
            QueuedBuild(name="run-a", kind="interactive", arrived=0)
        )
        queue.submit(
            QueuedBuild(name="run-b", kind="interactive", arrived=1)
        )
        queue.submit(
            QueuedBuild(name="dev-late", kind="interactive", arrived=9)
        )
        queue.submit(
            QueuedBuild(name="dev-early", kind="interactive", arrived=2)
        )
        assert [held.name for held in queue.waiting] == [
            "dev-early",
            "dev-late",
        ]

    def test_finish_promotes_the_head_of_the_queue(self):
        queue = full_farm()
        queue.submit(
            QueuedBuild(name="dev", kind="interactive", arrived=2)
        )
        promoted = queue.finish("batch-a")
        assert promoted == "dev"
        assert "dev" in queue.running

    def test_finishing_the_absent_is_refused(self):
        with pytest.raises(Invalid):
            full_farm().finish("ghost")


class TestPatience:
    def test_three_bumps_promote_the_nightly(self):
        queue = full_farm()
        for round_number in range(3):
            first = f"d1r{round_number}"
            second = f"d2r{round_number}"
            queue.submit(
                QueuedBuild(
                    name=first,
                    kind="interactive",
                    arrived=100 + 2 * round_number,
                )
            )
            outcome = queue.submit(
                QueuedBuild(
                    name=second,
                    kind="interactive",
                    arrived=101 + 2 * round_number,
                )
            )
            assert "preempting batch-b" in outcome
            queue.finish(second)
            if round_number < 2:
                queue.finish(first)
        assert "batch-b" in queue.promotions
        assert queue.running["batch-b"].kind == "interactive"
        assert queue.bill() == (
            "3 preemptions, 15 work ticks thrown away, "
            "1 batch jobs promoted by patience"
        )
