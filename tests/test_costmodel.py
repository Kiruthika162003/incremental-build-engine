from __future__ import annotations

import pytest

from forge.costmodel import CostModel
from forge.errors import Invalid


class TestLearning:
    def test_the_first_observation_is_the_estimate(self):
        model = CostModel()
        model.observe("main.o", "cc", 10)
        estimate, confidence = model.estimate("main.o", "cc")
        assert estimate == 10.0
        assert confidence == "single observation"

    def test_the_blend_leans_toward_the_recent(self):
        model = CostModel()
        model.observe("main.o", "cc", 10)
        model.observe("main.o", "cc", 20)
        estimate, confidence = model.estimate("main.o", "cc")
        assert estimate == 13.0
        assert confidence == "2 observations"

    def test_an_upgrade_outweighs_ancient_history(self):
        model = CostModel()
        for _ in range(20):
            model.observe("main.o", "cc", 10)
        for _ in range(10):
            model.observe("main.o", "cc", 30)
        estimate, _ = model.estimate("main.o", "cc")
        assert estimate > 28

    def test_negative_durations_are_refused(self):
        with pytest.raises(Invalid):
            CostModel().observe("x", "cc", -1)


class TestInheritance:
    def test_the_newcomer_inherits_the_family_median(self):
        model = CostModel()
        model.observe("a.pb", "protoc", 4)
        model.observe("b.pb", "protoc", 8)
        model.observe("c.pb", "protoc", 100)
        estimate, confidence = model.estimate("new.pb", "protoc")
        assert estimate == 8.0
        assert confidence == "inherited from the protoc family"

    def test_an_orphan_with_no_family_is_refused(self):
        model = CostModel()
        with pytest.raises(Invalid, match="run it once"):
            model.estimate("first.rs", "rustc")

    def test_families_do_not_cross(self):
        model = CostModel()
        model.observe("a.o", "cc", 10)
        with pytest.raises(Invalid):
            model.estimate("new.pb", "protoc")


class TestDrift:
    def test_the_slowed_rule_is_named_with_direction(self):
        model = CostModel()
        model.observe("main.o", "cc", 10)
        report = model.drift_report({"main.o": 25})
        assert report == [
            "main.o: estimated 10.0, ran 25; someone made a fast "
            "rule slow"
        ]

    def test_the_suddenly_fast_rule_is_also_news(self):
        model = CostModel()
        model.observe("main.o", "cc", 40)
        report = model.drift_report({"main.o": 10})
        assert "slow rule fast" in report[0]

    def test_the_neighbourhood_absorbs_normal_wobble(self):
        model = CostModel()
        model.observe("main.o", "cc", 10)
        assert model.drift_report({"main.o": 15}) == []
