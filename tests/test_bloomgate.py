from __future__ import annotations

import pytest

from forge.bloomgate import BloomGate
from forge.errors import Invalid


def loaded_gate() -> BloomGate:
    gate = BloomGate()
    for number in range(40):
        gate.publish(f"stored{number}")
    return gate


class TestTheThreeAnswers:
    def test_absence_is_provable_locally(self):
        gate = BloomGate()
        gate.publish("stored0")
        verdict = gate.lookup("neverstored")
        assert "definitely not remote" in verdict
        assert gate.skipped_trips == 1

    def test_a_stored_key_is_a_maybe_then_a_hit(self):
        gate = loaded_gate()
        assert gate.lookup("stored5") == (
            "stored5: maybe said the filter, hit said the cache"
        )

    def test_no_stored_key_is_ever_denied(self):
        gate = loaded_gate()
        for number in range(40):
            verdict = gate.lookup(f"stored{number}")
            assert "definitely not" not in verdict


class TestTheMeasuredEconomics:
    def test_the_fixed_probe_set_meters_the_real_rate(self):
        gate = loaded_gate()
        for number in range(60):
            gate.lookup(f"probe{number}")
        for number in range(10):
            gate.lookup(f"stored{number}")
        assert gate.skipped_trips == 57
        assert gate.paid_trips == 13
        assert gate.false_positives == 3
        ledger = gate.ledger()
        assert (
            "57 trip(s) skipped saving 1425 tick(s), 13 paid, "
            "3 false positive(s) (23% of travels)"
        ) in ledger

    def test_an_unused_gate_has_no_ledger(self):
        with pytest.raises(Invalid):
            BloomGate().ledger()

    def test_an_overfull_bitmap_warns_about_always_maybe(self):
        gate = BloomGate()
        for number in range(200):
            gate.publish(f"flood{number}")
        gate.lookup("flood0")
        assert "drifting toward always-maybe" in gate.ledger()
