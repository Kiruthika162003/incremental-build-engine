from __future__ import annotations

import pytest

from forge.dualread import DualReader
from forge.errors import Invalid

KEYS = {f"artifact{n}": f"digest{n}" for n in range(150)}


def reader(new_overrides=None) -> DualReader:
    new = dict(KEYS)
    if new_overrides:
        new.update(new_overrides)
    return DualReader(old_store=dict(KEYS), new_store=new)


class TestTheEra:
    def test_the_user_is_always_served_the_old_truth(self):
        chosen = reader(new_overrides={"artifact3": "WRONG"})
        assert chosen.read("artifact3") == "digest3"
        assert chosen.unexplained

    def test_agreements_bank_toward_the_quorum(self):
        chosen = reader()
        for n in range(50):
            chosen.read(f"artifact{n}")
        assert chosen.cutover_gate().startswith(
            "HOLD: 50 of 100 comparisons banked"
        )

    def test_a_missing_old_key_is_refused(self):
        with pytest.raises(Invalid):
            reader().read("ghost")


class TestTheGate:
    def test_the_full_era_cuts_over(self):
        chosen = reader()
        for n in range(120):
            chosen.read(f"artifact{n % 150}")
        verdict = chosen.cutover_gate()
        assert verdict.startswith(
            "CUT OVER: 120 comparisons, streak 120"
        )

    def test_one_unexplained_disagreement_holds_forever(self):
        chosen = reader(new_overrides={"artifact7": "WRONG"})
        for n in range(120):
            chosen.read(f"artifact{n % 150}")
        verdict = chosen.cutover_gate()
        assert verdict.startswith("HOLD: 1 unexplained")
        assert "before it answers alone" in verdict

    def test_lag_excuses_pause_the_streak_not_the_era(self):
        chosen = reader(new_overrides={"artifact99": "STALE"})
        for n in range(99):
            chosen.read(f"artifact{n}")
        chosen.read("artifact99", lag_excused=True)
        for n in range(10):
            chosen.read(f"artifact{n}")
        verdict = chosen.cutover_gate()
        assert verdict.startswith(
            "HOLD: the clean streak is 10 of 25"
        )
        assert chosen.unexplained == []
