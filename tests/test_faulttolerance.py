from __future__ import annotations

import pytest

from forge.errors import Invalid, Stale
from forge.faulttolerance import HEARTBEAT_DEADLINE, FaultTracker


def leased_farm() -> FaultTracker:
    tracker = FaultTracker()
    tracker.lease("compile-a", "w0", now=0)
    tracker.lease("compile-b", "w0", now=0)
    tracker.lease("compile-c", "w1", now=0)
    return tracker


class TestLeasing:
    def test_completion_retires_the_lease(self):
        tracker = leased_farm()
        tracker.complete("compile-a")
        assert "compile-a" not in tracker.leases
        assert tracker.completed == ["compile-a"]

    def test_double_leasing_is_refused(self):
        tracker = leased_farm()
        with pytest.raises(Invalid, match="already leased"):
            tracker.lease("compile-a", "w1", now=1)

    def test_completing_the_unleased_is_refused(self):
        with pytest.raises(Invalid):
            FaultTracker().complete("ghost")


class TestDeath:
    def test_the_silent_worker_is_declared_dead_once(self):
        tracker = leased_farm()
        tracker.heartbeat("w1", now=8)
        freed = tracker.patrol(now=HEARTBEAT_DEADLINE)
        assert freed == ["compile-a", "compile-b"]
        assert tracker.dead == {"w0"}
        assert tracker.patrol(now=HEARTBEAT_DEADLINE + 1) == []

    def test_the_living_keep_their_leases(self):
        tracker = leased_farm()
        tracker.heartbeat("w1", now=8)
        tracker.patrol(now=HEARTBEAT_DEADLINE)
        assert "compile-c" in tracker.leases

    def test_a_late_heartbeat_does_not_resurrect(self):
        tracker = leased_farm()
        tracker.heartbeat("w1", now=8)
        tracker.patrol(now=HEARTBEAT_DEADLINE)
        with pytest.raises(Stale, match="does not resurrect"):
            tracker.heartbeat("w0", now=HEARTBEAT_DEADLINE + 1)

    def test_nothing_leases_to_the_dead(self):
        tracker = leased_farm()
        tracker.heartbeat("w1", now=8)
        tracker.patrol(now=HEARTBEAT_DEADLINE)
        with pytest.raises(Invalid, match="is dead"):
            tracker.lease("compile-d", "w0", now=11)


class TestConservation:
    def test_every_action_is_completed_or_returned_never_both(self):
        tracker = leased_farm()
        tracker.complete("compile-c")
        tracker.patrol(now=HEARTBEAT_DEADLINE)
        assert tracker.conservation_holds(
            ["compile-a", "compile-b", "compile-c"]
        )

    def test_a_lost_action_breaks_conservation_loudly(self):
        tracker = leased_farm()
        tracker.complete("compile-a")
        tracker.returned.append("compile-a")
        assert not tracker.conservation_holds(["compile-a"])

    def test_the_bill_reads_the_failure(self):
        tracker = leased_farm()
        tracker.complete("compile-c")
        tracker.heartbeat("w1", now=8)
        tracker.patrol(now=HEARTBEAT_DEADLINE)
        assert tracker.bill() == (
            "1 workers lost, 2 actions re-dispatched, 1 completed"
        )
