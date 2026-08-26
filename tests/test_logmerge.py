from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.logmerge import LogMerger

ORDER = ["lib.o", "main.o", "app"]


def scrambled_run(merger: LogMerger) -> None:
    """Workers finish in a different order than the graph's."""
    merger.emit("main.o", "compiling main.c")
    merger.emit("lib.o", "compiling lib.c")
    merger.emit("main.o", "main.o written")
    merger.complete("main.o")
    merger.emit("lib.o", "lib.o written")
    merger.complete("lib.o")
    merger.emit("app", "linking")
    merger.complete("app")


class TestDeterminism:
    def test_the_merged_log_follows_the_graph_not_the_workers(self):
        merger = LogMerger(order=list(ORDER))
        scrambled_run(merger)
        assert merger.merged().splitlines() == [
            "=== lib.o ===",
            "compiling lib.c",
            "lib.o written",
            "=== main.o ===",
            "compiling main.c",
            "main.o written",
            "=== app ===",
            "linking",
        ]

    def test_two_scrambles_produce_one_log(self):
        first = LogMerger(order=list(ORDER))
        scrambled_run(first)
        second = LogMerger(order=list(ORDER))
        second.emit("lib.o", "compiling lib.c")
        second.emit("lib.o", "lib.o written")
        second.complete("lib.o")
        second.emit("main.o", "compiling main.c")
        second.emit("main.o", "main.o written")
        second.complete("main.o")
        second.emit("app", "linking")
        second.complete("app")
        assert first.is_deterministic_with(second)

    def test_lines_inside_an_action_keep_their_order(self):
        merger = LogMerger(order=list(ORDER))
        scrambled_run(merger)
        page = merger.merged()
        assert page.index("compiling main.c") < page.index(
            "main.o written"
        )


class TestFailures:
    def test_the_failing_block_reads_last(self):
        merger = LogMerger(order=list(ORDER))
        merger.emit("lib.o", "error: lib.c:4: broken")
        merger.complete("lib.o", failed=True)
        merger.emit("main.o", "compiled fine")
        merger.complete("main.o")
        lines = merger.merged().splitlines()
        assert lines[-2] == "=== lib.o ==="
        assert lines[-1] == "error: lib.c:4: broken"

    def test_two_failures_are_refused(self):
        merger = LogMerger(order=list(ORDER))
        merger.complete("lib.o", failed=True)
        with pytest.raises(Invalid, match="stops at the first"):
            merger.complete("main.o", failed=True)


class TestContracts:
    def test_strangers_cannot_log(self):
        with pytest.raises(Invalid, match="not part of this build"):
            LogMerger(order=list(ORDER)).emit("ghost", "hello")

    def test_logging_after_completion_is_refused(self):
        merger = LogMerger(order=list(ORDER))
        merger.complete("lib.o")
        with pytest.raises(Invalid, match="too late"):
            merger.emit("lib.o", "postscript")

    def test_an_unfinished_story_cannot_merge(self):
        merger = LogMerger(order=list(ORDER))
        merger.emit("lib.o", "compiling")
        with pytest.raises(Invalid, match="not over"):
            merger.merged()
