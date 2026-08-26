from __future__ import annotations

import pytest

from forge.errors import Invalid, Missing
from forge.graph import Graph
from forge.toolchains import UpgradePlanner


def shop() -> UpgradePlanner:
    graph = Graph()
    graph.declare("a.c")
    graph.declare("b.c")
    graph.declare("a.o", needs=("a.c",))
    graph.declare("b.o", needs=("b.c",))
    graph.declare("lib", needs=("a.o", "b.o"))
    graph.declare("app", needs=("lib",))
    planner = UpgradePlanner(graph=graph)
    planner.record("a.o", "cc -O2", cost=8)
    planner.record("b.o", "cc -O2", cost=8)
    planner.record("lib", "ar rcs", cost=2)
    planner.record("app", "ld -o", cost=4)
    return planner


class TestInvalidation:
    def test_the_compiler_bump_is_priced_before_the_button(self):
        count, ticks, survival = shop().invalidation("cc")
        assert count == 2
        assert ticks == 16
        assert survival == 0.5

    def test_a_tool_nobody_uses_is_a_free_upgrade(self):
        with pytest.raises(Missing, match="the upgrade is free"):
            shop().invalidation("javac")

    def test_an_empty_command_is_refused(self):
        planner = shop()
        with pytest.raises(Invalid):
            planner.record("app", "   ", cost=1)


class TestTheWaves:
    def test_the_invalidation_rolls_by_depth(self):
        waves = shop().waves("cc", "app")
        assert waves == [["a.o", "b.o"]]

    def test_a_deep_tool_rolls_in_stages(self):
        planner = shop()
        planner.record("lib", "cc -shared", cost=2)
        waves = planner.waves("cc", "app")
        assert waves == [["a.o", "b.o"], ["lib"]]


class TestTheReceipt:
    def test_the_linker_survives_the_compiler_bump(self):
        page = shop().receipt("cc", "app")
        assert "2 rules invalidated, 16 ticks to repay" in page
        assert "50% of the cache survives" in page
        assert "untouched: app, lib" in page

    def test_the_receipt_lists_the_waves(self):
        page = shop().receipt("cc", "app")
        assert "wave 0: a.o, b.o" in page
