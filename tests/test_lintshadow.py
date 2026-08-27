from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.lintshadow import ShadowRule


def rule() -> ShadowRule:
    return ShadowRule(name="no-bare-except")


class TestTheShadowTerm:
    def test_probation_must_be_served(self):
        chosen = rule()
        chosen.observe_week(400)
        assert chosen.promotion_gate() == (
            "no-bare-except: 1 of 3 probation week(s) served"
        )

    def test_stable_volume_promotes_with_the_precedent(self):
        chosen = rule()
        for count in (402, 400, 401):
            chosen.observe_week(count)
        verdict = chosen.promotion_gate()
        assert verdict.startswith("no-bare-except PROMOTED")
        assert "volume stable at 401" in verdict
        assert "the next rule's precedent" in verdict

    def test_live_velocity_wants_education_not_enforcement(self):
        chosen = rule()
        for count in (100, 160, 240):
            chosen.observe_week(count)
        verdict = chosen.promotion_gate()
        assert "volume still moving" in verdict
        assert "education before enforcement" in verdict

    def test_the_promoted_rule_leaves_the_shadow(self):
        chosen = rule()
        for count in (10, 10, 10):
            chosen.observe_week(count)
        chosen.promotion_gate()
        with pytest.raises(Invalid) as caught:
            chosen.observe_week(9)
        assert "shadows are for the unproven" in str(caught.value)

    def test_velocity_is_week_over_week(self):
        chosen = rule()
        chosen.observe_week(100)
        chosen.observe_week(93)
        assert chosen.velocity() == -7
