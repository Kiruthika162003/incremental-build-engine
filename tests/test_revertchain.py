from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.revertchain import RevertTracker


def tracker() -> RevertTracker:
    return RevertTracker()


class TestTheChain:
    def test_the_first_revert_is_hygiene(self):
        verdict = tracker().record_revert(
            "abc123", "asha", subject="parser-cache"
        )
        assert "hygiene, the fastest way to green" in verdict

    def test_the_second_link_names_both_authors(self):
        chosen = tracker()
        chosen.record_revert("abc123", "asha", "parser-cache")
        verdict = chosen.record_revert(
            "def456", "ben", "parser-cache"
        )
        assert "asha and ben should find each other" in verdict
        assert "rolling forward with a fix beats taking turns" in (
            verdict
        )

    def test_the_third_link_is_refused_for_the_record(self):
        chosen = tracker()
        chosen.record_revert("abc123", "asha", "parser-cache")
        chosen.record_revert("def456", "ben", "parser-cache")
        with pytest.raises(Invalid) as caught:
            chosen.record_revert("ghi789", "asha", "parser-cache")
        assert "two theories of the codebase" in str(caught.value)
        assert "the paper trail the postmortem will want" in (
            str(caught.value)
        )

    def test_unrelated_subjects_do_not_chain(self):
        chosen = tracker()
        chosen.record_revert("abc", "asha", "parser-cache")
        verdict = chosen.record_revert("def", "ben", "linker-flag")
        assert "hygiene" in verdict


class TestDisputes:
    def test_only_multi_link_chains_are_disputes(self):
        chosen = tracker()
        chosen.record_revert("a", "asha", "parser-cache")
        chosen.record_revert("b", "ben", "parser-cache")
        chosen.record_revert("c", "chen", "linker-flag")
        assert chosen.open_disputes() == [
            "parser-cache: 2 link(s)"
        ]
