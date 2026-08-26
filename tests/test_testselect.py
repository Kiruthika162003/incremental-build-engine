from __future__ import annotations

import pytest

from forge.errors import Missing
from forge.graph import Graph
from forge.testselect import Selector


def repository() -> Selector:
    graph = Graph()
    graph.declare("auth.c")
    graph.declare("billing.c")
    graph.declare("shared.c")
    graph.declare("auth.o", needs=("auth.c", "shared.c"))
    graph.declare("billing.o", needs=("billing.c", "shared.c"))
    graph.declare("auth_test", needs=("auth.o",))
    graph.declare("billing_test", needs=("billing.o",))
    graph.declare("weather_test")
    selector = Selector(graph=graph)
    for name in ("auth_test", "billing_test", "weather_test"):
        selector.mark_test(name)
    return selector


class TestSelection:
    def test_a_leaf_edit_selects_only_its_cone(self):
        selection = repository().select(["auth.c"])
        assert selection.selected == ["auth_test"]
        assert "billing_test" in selection.skipped

    def test_a_shared_edit_selects_both_sides(self):
        selection = repository().select(["shared.c"])
        assert selection.selected == ["auth_test", "billing_test"]

    def test_editing_a_test_selects_itself(self):
        selection = repository().select(["auth_test"])
        assert selection.selected == ["auth_test"]

    def test_an_unknown_change_is_refused(self):
        with pytest.raises(Missing, match="never heard"):
            repository().select(["mystery.c"])

    def test_the_refund_is_skipped_over_total(self):
        selection = repository().select(["auth.c"])
        assert selection.refund() == pytest.approx(2 / 3)
        assert selection.line() == (
            "1 changed: run 1, skip 2 (67% refund)"
        )


class TestOrphans:
    def test_the_weather_test_is_named(self):
        selection = repository().select(["auth.c"])
        assert selection.orphans == ["weather_test"]

    def test_wired_tests_are_not_orphans(self):
        orphans = repository().orphan_tests()
        assert "auth_test" not in orphans
        assert "billing_test" not in orphans
