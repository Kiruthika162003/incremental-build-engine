from __future__ import annotations

import pytest

from forge.branchcache import BranchCache, merge_back
from forge.errors import Invalid

MAIN = {"compile:core": "d1", "compile:app": "d2", "link:app": "d3"}


def branch() -> BranchCache:
    return BranchCache(branch="feature-x", main_entries=dict(MAIN))


class TestTheOverlay:
    def test_untouched_keys_read_through_to_main(self):
        cache = branch()
        assert cache.lookup("compile:core") == "d1"
        assert cache.inherited_hits == 1

    def test_the_branch_writes_only_its_own_layer(self):
        cache = branch()
        cache.store("compile:core", "branch-d1")
        assert cache.lookup("compile:core") == "branch-d1"
        assert cache.main_entries["compile:core"] == "d1"

    def test_a_redundant_copy_is_declined(self):
        cache = branch()
        verdict = cache.store("compile:core", "d1")
        assert "declines a redundant copy" in verdict
        assert cache.overlay == {}

    def test_a_novel_key_misses_both_layers(self):
        cache = branch()
        assert cache.lookup("compile:new-file") is None
        assert cache.misses == 1

    def test_poison_is_structurally_impossible(self):
        cache = branch()
        cache.store("compile:core", "branch-d1")
        assert cache.poison_check() == (
            "1 key(s) shadowed with different bytes; main's "
            "copies are untouched by construction"
        )


class TestTheLedger:
    def test_a_cheap_branch_is_told_it_rides_main(self):
        cache = branch()
        cache.lookup("compile:core")
        cache.lookup("compile:app")
        cache.store("compile:core", "x")
        cache.lookup("compile:core")
        report = cache.ledger()
        assert "2 inherited hit(s), 1 owned" in report
        assert "riding main's work" in report

    def test_the_rebase_hint_appears_past_half_owned(self):
        cache = branch()
        cache.store("compile:core", "x")
        cache.store("compile:app", "y")
        cache.lookup("compile:core")
        cache.lookup("compile:app")
        cache.lookup("link:app")
        report = cache.ledger()
        assert "owned share 67%" in report
        assert "rebase to return to the cheap side" in report

    def test_no_hits_cannot_be_characterized(self):
        with pytest.raises(Invalid):
            branch().ledger()


class TestMergeBack:
    def test_novel_results_promote_and_stale_twins_drop(self):
        cache = branch()
        cache.store("compile:core", "branch-d1")
        cache.store("compile:brandnew", "d9")
        cache.overlay["link:app"] = "d3"
        promoted, dropped = merge_back(cache)
        assert (promoted, dropped) == (2, 1)
        assert cache.main_entries["compile:core"] == "branch-d1"
        assert cache.main_entries["compile:brandnew"] == "d9"
        assert cache.overlay == {}
