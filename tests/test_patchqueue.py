from __future__ import annotations

import pytest

from forge.errors import Invalid, Stale
from forge.patchqueue import Patch, PatchQueue

BASE = "alpha\nbeta\ngamma\ndelta\n"


def queue_with_two() -> PatchQueue:
    queue = PatchQueue()
    queue.add(
        Patch.against(BASE, "fix-beta", "beta", "beta-fixed")
    )
    queue.add(
        Patch.against(BASE, "drop-delta", "delta\n", "")
    )
    return queue


class TestWritingPatches:
    def test_a_patch_against_absent_text_is_refused(self):
        with pytest.raises(Invalid):
            Patch.against(BASE, "ghost", "omega", "x")

    def test_an_ambiguous_patch_is_refused(self):
        with pytest.raises(Invalid):
            Patch.against("dup dup", "twice", "dup", "x")

    def test_duplicate_titles_are_refused(self):
        queue = queue_with_two()
        with pytest.raises(Invalid):
            queue.add(
                Patch.against(BASE, "fix-beta", "alpha", "a")
            )


class TestApplication:
    def test_patches_apply_in_order_and_all_land(self):
        queue = queue_with_two()
        result = queue.apply(BASE)
        assert "beta-fixed" in result
        assert "delta" not in result
        assert queue.applied_titles == ["fix-beta", "drop-delta"]

    def test_a_later_patch_sees_the_earlier_ones_text(self):
        queue = PatchQueue()
        queue.add(Patch.against(BASE, "one", "beta", "middle"))
        queue.add(
            Patch(
                title="two",
                find="middle",
                replace="middle-more",
                context_digest="x" * 64,
            )
        )
        assert "middle-more" in queue.apply(BASE)


class TestUpstreamMoves:
    def test_staleness_is_named_by_title_before_anyone_builds(self):
        queue = queue_with_two()
        moved = BASE.replace("beta", "second")
        assert queue.stale_against(moved) == ["fix-beta"]

    def test_a_rename_keeping_the_substring_slips_past(self):
        queue = queue_with_two()
        moved = BASE.replace("beta", "brand-new-beta")
        assert queue.stale_against(moved) == []
        assert "brand-new-beta-fixed" in queue.apply(moved)

    def test_applying_stale_patches_refuses_loudly(self):
        queue = queue_with_two()
        with pytest.raises(Stale) as caught:
            queue.apply(BASE.replace("beta", "changed"))
        assert "fix-beta" in str(caught.value)
        assert "rebase them before building" in str(caught.value)

    def test_an_upstreamed_patch_is_retired_by_rebase(self):
        queue = queue_with_two()
        merged = BASE.replace("delta\n", "")
        queue.rebase("drop-delta", merged)
        assert "drop-delta" not in [
            patch.title for patch in queue.patches
        ]
        assert len(queue.patches) == 1

    def test_a_rebase_the_patch_does_not_need_is_refused(self):
        queue = queue_with_two()
        with pytest.raises(Invalid):
            queue.rebase("fix-beta", BASE)

    def test_rebasing_a_stranger_is_refused(self):
        with pytest.raises(Invalid):
            queue_with_two().rebase("ghost", BASE)


class TestTheLedger:
    def test_the_ledger_names_titles_and_contexts(self):
        report = queue_with_two().ledger()
        assert report.startswith("2 patch(es) queued")
        assert "fix-beta (context " in report

    def test_the_empty_queue_credits_upstream(self):
        assert PatchQueue().ledger() == (
            "the queue is empty; upstream owns every line"
        )
