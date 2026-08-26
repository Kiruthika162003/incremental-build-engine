from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.mergequeue import QueueLedger, conflicts_with, run_queue

CHANGES = [f"pr{number}" for number in range(8)]


class TestGreenBatches:
    def test_a_clean_batch_merges_for_one_build(self):
        ledger = run_queue(CHANGES, conflicts_with(set()))
        assert ledger.builds == 1
        assert ledger.merged == CHANGES
        assert ledger.price() == (
            "1 builds for 8 merges (0.12 builds per change), 0 exiled"
        )


class TestOneBadApple:
    def test_the_culprit_is_exiled_by_name(self):
        ledger = run_queue(CHANGES, conflicts_with({"pr5"}))
        assert ledger.exiled == ["pr5"]
        assert sorted(ledger.merged) == sorted(
            change for change in CHANGES if change != "pr5"
        )

    def test_the_innocent_still_merge_cheaply(self):
        ledger = run_queue(CHANGES, conflicts_with({"pr5"}))
        assert ledger.builds == 7

    def test_two_culprits_double_the_hunt_not_the_exiles(self):
        ledger = run_queue(CHANGES, conflicts_with({"pr1", "pr6"}))
        assert sorted(ledger.exiled) == ["pr1", "pr6"]
        assert len(ledger.merged) == 6


class TestTheWorstCase:
    def test_all_broken_degenerates_to_serial_and_says_so(self):
        ledger = run_queue(CHANGES, conflicts_with(set(CHANGES)))
        assert ledger.merged == []
        assert len(ledger.exiled) == 8
        assert ledger.builds == 15
        assert "inf builds per change" in ledger.price()

    def test_an_empty_queue_is_refused(self):
        with pytest.raises(Invalid):
            run_queue([], conflicts_with(set()))

    def test_an_unprocessed_ledger_has_no_price(self):
        with pytest.raises(Invalid):
            QueueLedger().price()
