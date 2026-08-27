from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.wal import Journal


def journal() -> Journal:
    built = Journal()
    built.append("core.o", "digest-1")
    built.append("app", "digest-2")
    built.append("core.o", "digest-3")
    return built


class TestRecovery:
    def test_a_healthy_journal_replays_the_last_state(self):
        state, verdict = journal().recover()
        assert state == {"core.o": "digest-3", "app": "digest-2"}
        assert verdict == "3 record(s), no tear"

    def test_the_torn_tail_is_amputated_with_a_count(self):
        built = journal()
        built.simulate_torn_tail()
        state, verdict = built.recover()
        assert state == {"core.o": "digest-1", "app": "digest-2"}
        assert verdict.startswith(
            "2 record(s) survived, 1 amputated"
        )
        assert "the only sin is replaying it" in verdict

    def test_recovery_is_idempotent(self):
        built = journal()
        built.simulate_torn_tail()
        built.recover()
        assert built.replay_twice_agrees()

    def test_separator_keys_are_refused(self):
        with pytest.raises(Invalid):
            Journal().append("bad|key", "x")


class TestCompaction:
    def test_a_short_journal_declines_to_churn(self):
        assert "churn for nothing" in journal().compact()

    def test_a_long_journal_becomes_one_snapshot(self):
        built = journal()
        for round_number in range(5):
            built.append("app", f"digest-{round_number}")
        verdict = built.compact()
        assert verdict.startswith(
            "compacted to 1 snapshot record holding 2 key(s)"
        )
        assert len(built.records) == 1

    def test_the_snapshot_replays_to_the_same_state(self):
        built = journal()
        for round_number in range(5):
            built.append("app", f"digest-{round_number}")
        before, _ = built.recover()
        built.compact()
        after, _ = built.recover()
        assert after == before

    def test_the_snapshot_pays_the_same_toll(self):
        built = journal()
        for round_number in range(5):
            built.append("app", f"digest-{round_number}")
        built.compact()
        built.simulate_torn_tail()
        state, verdict = built.recover()
        assert state == {}
        assert "1 amputated" in verdict
