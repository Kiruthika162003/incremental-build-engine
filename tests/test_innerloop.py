from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.innerloop import InnerLoop


def bimodal_day() -> InnerLoop:
    loop = InnerLoop()
    for _ in range(15):
        loop.record(2)
    for _ in range(5):
        loop.record(90)
    return loop


class TestTheSummary:
    def test_the_bimodal_day_refuses_the_single_number(self):
        summary = bimodal_day().summary()
        assert summary.startswith("bimodal at least")
        assert "15 edit(s) near 2" in summary
        assert "5 edit(s) near 90" in summary
        assert "describes nobody's edit" in summary

    def test_the_mean_is_named_and_disowned(self):
        assert "24-tick mean" in bimodal_day().summary()

    def test_a_unimodal_day_keeps_the_mean(self):
        loop = InnerLoop()
        for ticks in (8, 9, 10, 11):
            loop.record(ticks)
        summary = loop.summary()
        assert summary.startswith("unimodal")
        assert "the mean is honest today" in summary

    def test_an_empty_day_is_refused(self):
        with pytest.raises(Invalid):
            InnerLoop().summary()

    def test_instant_feedback_is_refused_as_a_lie(self):
        with pytest.raises(Invalid):
            InnerLoop().record(0)


class TestTheFlowVerdict:
    def test_the_cliff_fraction_is_the_headline(self):
        verdict = bimodal_day().flow_verdict()
        assert "15 of 20 edit(s) kept flow" in verdict
        assert "5 crossed the abandonment cliff" in verdict
        assert "25% of edits losing the developer" in verdict

    def test_a_fast_day_loses_nobody(self):
        loop = InnerLoop()
        for _ in range(4):
            loop.record(3)
        assert "0% of edits losing the developer" in (
            loop.flow_verdict()
        )
