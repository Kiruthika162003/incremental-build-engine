from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.loadtest import TrafficMix, divergences, grade, realism

PRODUCTION = TrafficMix(
    shares={"compile": 0.6, "link": 0.1, "test": 0.3}
)
HAMMER = TrafficMix(shares={"compile": 1.0})
FAITHFUL = TrafficMix(
    shares={"compile": 0.55, "link": 0.15, "test": 0.3}
)


class TestRealism:
    def test_the_hammer_scores_its_overlap_only(self):
        assert realism(PRODUCTION, HAMMER) == pytest.approx(0.6)

    def test_the_faithful_mix_scores_high(self):
        assert realism(PRODUCTION, FAITHFUL) == pytest.approx(
            0.95
        )

    def test_shares_must_sum_to_one(self):
        with pytest.raises(Invalid):
            TrafficMix(shares={"compile": 0.5})


class TestDivergences:
    def test_each_divergence_names_its_direction(self):
        found = divergences(PRODUCTION, HAMMER)
        assert (
            "compile: 100% synthetic against 60% production "
            "(over-represented)"
        ) in found
        assert (
            "test: 0% synthetic against 30% production "
            "(missing)"
        ) in found


class TestTheGrade:
    def test_the_unrealistic_number_is_withheld_not_footnoted(self):
        verdict = grade(PRODUCTION, HAMMER, 900)
        assert verdict.startswith("WITHHELD: realism 60%")
        assert "outlives the caveat" in verdict
        assert "900" not in verdict

    def test_the_faithful_test_reports_one_inseparable_line(self):
        verdict = grade(PRODUCTION, FAITHFUL, 480)
        assert verdict == (
            "throughput 480/tick at realism 95%; one line, "
            "inseparable"
        )
