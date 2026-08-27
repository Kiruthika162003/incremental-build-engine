from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.pulse import PulsePage


def page() -> PulsePage:
    built = PulsePage()
    built.rate("coordinator", "up")
    built.rate("cache", "up")
    built.rate("store", "up")
    return built


class TestRating:
    def test_degraded_demands_its_symptom(self):
        with pytest.raises(Invalid) as caught:
            PulsePage().rate("store", "degraded")
        assert "dashboards become decorations" in str(
            caught.value
        )

    def test_a_pulse_with_missing_organs_is_a_guess(self):
        built = PulsePage()
        built.rate("coordinator", "up")
        with pytest.raises(Invalid) as caught:
            built.overall()
        assert "cache, store unrated" in str(caught.value)


class TestOverall:
    def test_the_green_morning_reads_plainly(self):
        assert page().overall() == "all user-visible paths up"

    def test_the_worst_component_wins_never_the_average(self):
        built = page()
        built.rate("store", "down")
        verdict = built.overall()
        assert verdict.startswith("down: store")
        assert "describes nobody's morning" in verdict

    def test_degraded_carries_its_symptom_into_the_verdict(self):
        built = page()
        built.rate(
            "cache", "degraded", symptom="uploads timing out"
        )
        assert (
            "degraded: cache (uploads timing out)"
        ) in built.overall()


class TestTheRealityCheck:
    def test_the_contradiction_sides_with_reality(self):
        verdict = page().reality_check(budget_burning=True)
        assert verdict.startswith(
            "CONTRADICTION: green dashboard, degraded reality"
        )
        assert "sides with reality" in verdict

    def test_agreement_is_one_quiet_line(self):
        assert page().reality_check(budget_burning=False) == (
            "the page and the meters agree"
        )
