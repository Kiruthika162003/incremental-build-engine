from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.iocensus import IoCensus


def busy_build() -> IoCensus:
    census = IoCensus()
    census.observe(
        "compile-a",
        reads=("common.h", "a.c"),
        writes=("a.o",),
    )
    census.observe(
        "compile-b",
        reads=("common.h", "b.c"),
        writes=("b.o",),
    )
    census.observe(
        "compile-c",
        reads=("common.h", "c.c"),
        writes=("c.o",),
    )
    census.observe(
        "link",
        reads=("a.o", "b.o", "c.o", "libm.a"),
        writes=("app",),
    )
    return census


class TestTheTwoNames:
    def test_the_hottest_file_is_the_shared_header(self):
        verdict = busy_build().hottest_file()
        assert verdict.startswith(
            "common.h is read by 3 action(s)"
        )
        assert "split it or precompile it" in verdict

    def test_the_hungriest_action_is_the_link(self):
        verdict = busy_build().hungriest_action()
        assert verdict.startswith("link reads 4 file(s)")
        assert "freight bill" in verdict

    def test_duplicate_reads_count_once(self):
        census = IoCensus()
        census.observe(
            "odd", reads=("x.h", "x.h", "x.h"), writes=("o",)
        )
        assert "odd reads 1 file(s)" in census.hungriest_action()


class TestCollisions:
    def test_a_clean_build_has_none(self):
        assert busy_build().write_collisions() == []

    def test_the_collision_names_both_writers(self):
        census = busy_build()
        census.observe(
            "sneaky", reads=(), writes=("a.o",)
        )
        assert census.write_collisions() == [
            "a.o written by compile-a, sneaky"
        ]
        assert "for the conflict detector" in census.report()


class TestRefusals:
    def test_double_observation_is_refused(self):
        census = busy_build()
        with pytest.raises(Invalid):
            census.observe("link", reads=(), writes=())

    def test_an_empty_census_has_no_names(self):
        with pytest.raises(Invalid):
            IoCensus().hottest_file()
