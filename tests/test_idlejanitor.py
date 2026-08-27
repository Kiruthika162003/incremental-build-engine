from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.idlejanitor import IdleJanitor


def janitor() -> IdleJanitor:
    built = IdleJanitor()
    built.add_chore("warm-the-core-cone", 30)
    built.add_chore("certify-flaky-stamper", 10)
    built.add_chore("cleanroom-slice", 20, insurance=True)
    return built


class TestChoreOrder:
    def test_insurance_runs_before_convenience(self):
        verdict = janitor().idle_gap(5)
        assert verdict.startswith(
            "gap of 5: cleanroom-slice (5)"
        )

    def test_a_long_gap_flows_through_the_queue(self):
        verdict = janitor().idle_gap(35)
        assert "cleanroom-slice (20)" in verdict
        assert "certify-flaky-stamper (10)" in verdict
        assert "warm-the-core-cone (5)" in verdict

    def test_an_empty_queue_leaves_the_gap_idle(self):
        chosen = IdleJanitor()
        assert chosen.idle_gap(10) == (
            "no chores; the gap stays idle"
        )

    def test_a_done_chore_is_refused_at_the_door(self):
        with pytest.raises(Invalid):
            IdleJanitor().add_chore("nothing", 0)


class TestYielding:
    def test_the_chore_yields_with_its_progress_kept(self):
        chosen = janitor()
        chosen.idle_gap(5)
        verdict = chosen.real_work_arrives()
        assert verdict == (
            "cleanroom-slice yields immediately with 15 "
            "tick(s) kept, requeued at its front, not restarted"
        )

    def test_yielding_from_a_clear_hallway_is_fine(self):
        chosen = IdleJanitor()
        assert chosen.real_work_arrives() == (
            "the hallway was already clear"
        )


class TestTheLedger:
    def test_the_week_reads_like_an_honest_janitor(self):
        chosen = janitor()
        chosen.idle_gap(30)
        chosen.real_work_arrives()
        ledger = chosen.week_ledger()
        assert "2 chore(s) finished using 30 idle tick(s)" in (
            ledger
        )
        assert "1 yield(s)" in ledger
        assert "standing aside: warm-the-core-cone" in ledger
        assert "real work waited 0 tick(s)" in ledger
        assert "the janitor's whole contract" in ledger
