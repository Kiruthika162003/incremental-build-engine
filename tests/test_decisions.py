from __future__ import annotations

import pytest

from forge.decisions import Chronicle
from forge.errors import Invalid


def chronicle() -> Chronicle:
    built = Chronicle()
    built.record(
        "retry-count-4",
        why="3 lost to the flaky rack, 5 doubled queue time",
        decided_on_day=100,
    )
    built.record(
        "retry-count-2",
        why="the flaky rack was retired",
        decided_on_day=900,
    )
    built.supersede("retry-count-4", "retry-count-2")
    return built


class TestTheChain:
    def test_the_why_survives_its_author(self):
        assert chronicle().why("retry-count-2") == (
            "retry-count-2: the flaky rack was retired"
        )

    def test_the_superseded_why_is_kept_not_erased(self):
        answer = chronicle().why("retry-count-4")
        assert "superseded by retry-count-2" in answer
        assert "3 lost to the flaky rack" in answer

    def test_memory_is_not_a_storage_tier(self):
        with pytest.raises(Invalid) as caught:
            chronicle().why("timeout-90")
        assert "not a storage tier" in str(caught.value)

    def test_a_whyless_decision_is_refused(self):
        with pytest.raises(Invalid):
            Chronicle().record("x", why=" ", decided_on_day=1)

    def test_chains_grow_at_the_head(self):
        built = chronicle()
        with pytest.raises(Invalid):
            built.supersede("retry-count-4", "retry-count-9")


class TestTheLint:
    def test_a_whole_chronicle_says_so(self):
        assert chronicle().lint(today=1000) == (
            "the chronicle is whole"
        )

    def test_the_broken_promise_is_the_classic_rot(self):
        built = chronicle()
        built.decisions["retry-count-4"]["superseded_by"] = (
            "retry-count-ghost"
        )
        report = built.lint(today=1000)
        assert "1 broken promise(s)" in report
        assert "a promise of a reason, broken" in report

    def test_old_accepted_decisions_are_unexamined_not_wrong(self):
        built = Chronicle()
        built.record("keep-make", why="it works", decided_on_day=0)
        report = built.lint(today=800)
        assert "1 unexamined" in report
        assert "not wrong, unexamined" in report
