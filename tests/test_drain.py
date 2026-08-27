from __future__ import annotations

import pytest

from forge.drain import DrainingWorker
from forge.errors import Invalid


def worker() -> DrainingWorker:
    return DrainingWorker(
        name="rack4",
        running={"compile-a": 10, "link-app": 50, "test-b": 20},
        warm_state=("persistent-cc", "warm-cache-shard"),
    )


class TestTheContract:
    def test_draining_accepts_nothing_new(self):
        chosen = worker()
        chosen.begin_drain(deadline_ticks=30)
        with pytest.raises(Invalid) as caught:
            chosen.accept("compile-new")
        assert "the entire meaning of draining" in str(
            caught.value
        )

    def test_the_deadline_splits_finishers_from_evictions(self):
        chosen = worker()
        chosen.begin_drain(deadline_ticks=30)
        chosen.run_out()
        assert chosen.finished == ["compile-a", "test-b"]
        assert chosen.evicted == [
            "link-app requeued elsewhere: needed 50 against "
            "a deadline of 30"
        ]

    def test_a_zero_deadline_is_a_kill_in_disguise(self):
        with pytest.raises(Invalid) as caught:
            worker().begin_drain(deadline_ticks=0)
        assert "kill wearing a drain's name" in str(caught.value)

    def test_handing_off_mid_run_is_refused(self):
        chosen = worker()
        chosen.begin_drain(deadline_ticks=30)
        with pytest.raises(Invalid):
            chosen.hand_off("rack5")


class TestTheHandoff:
    def test_warmth_moves_to_the_successor(self):
        chosen = worker()
        chosen.begin_drain(deadline_ticks=100)
        chosen.run_out()
        verdict = chosen.hand_off("rack5")
        assert (
            "persistent-cc, warm-cache-shard handed to rack5"
        ) in verdict
        assert "not the machine's accumulated usefulness" in (
            verdict
        )

    def test_a_cold_worker_hands_over_nothing(self):
        chosen = DrainingWorker(
            name="rack9", running={}, warm_state=()
        )
        chosen.begin_drain(deadline_ticks=10)
        chosen.run_out()
        assert chosen.hand_off("rack5") == (
            "nothing warm to hand rack5"
        )


class TestTheTicket:
    def test_the_report_is_a_checkable_claim(self):
        chosen = worker()
        chosen.begin_drain(deadline_ticks=30)
        chosen.run_out()
        chosen.hand_off("rack5")
        report = chosen.ticket_report()
        assert report.startswith(
            "rack4 drained: 2 finished, 1 evicted, warmth to "
            "rack5"
        )
        assert "link-app requeued elsewhere" in report

    def test_an_unfinished_drain_has_no_report(self):
        with pytest.raises(Invalid):
            worker().ticket_report()
