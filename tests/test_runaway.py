from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.runaway import BuildCap


def cap() -> BuildCap:
    return BuildCap(ceiling_ticks=1000, honest_maximum=400)


class TestTheWall:
    def test_honest_builds_never_meet_the_wall(self):
        chosen = cap()
        for number in range(8):
            verdict = chosen.charge(f"compile-{number}", 50)
        assert verdict == "compile-7: 400 of 1000"
        assert not chosen.killed

    def test_the_runaway_is_killed_with_the_spender_named(self):
        chosen = cap()
        chosen.charge("compile-a", 300)
        chosen.charge("compile-b", 200)
        verdict = chosen.charge("codegen-loop", 600)
        assert verdict.startswith(
            "KILLED at 1100 of 1000 tick(s) across 3 action(s)"
        )
        assert "codegen-loop spent 54% of the budget" in verdict
        assert "a ticket and a fix" in verdict
        assert chosen.killed

    def test_the_dead_build_cannot_be_charged(self):
        chosen = cap()
        chosen.charge("everything", 1200)
        with pytest.raises(Invalid) as caught:
            chosen.charge("more", 10)
        assert "stop charging it" in str(caught.value)

    def test_a_stingy_ceiling_is_a_lottery(self):
        with pytest.raises(Invalid) as caught:
            BuildCap(ceiling_ticks=300, honest_maximum=400)
        assert "it is a lottery" in str(caught.value)

    def test_free_actions_are_refused(self):
        with pytest.raises(Invalid):
            cap().charge("ghost", 0)
