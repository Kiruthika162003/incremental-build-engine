from __future__ import annotations

import pytest

from forge.actions import Action
from forge.depprune import Pruner
from forge.errors import Invalid
from forge.graph import Graph


def action(name: str, reads: tuple, writes: tuple) -> Action:
    return Action(
        name=name,
        command="tool",
        reads=reads,
        writes=writes,
        rule=lambda _tree: None,
    )


def wired() -> Pruner:
    graph = Graph()
    graph.declare("used.h")
    graph.declare("unused.h")
    graph.declare(
        "main.o", needs=("used.h", "unused.h")
    )
    actions = {
        "main.o": action(
            "main.o", ("used.h", "unused.h"), ("main.o",)
        ),
    }
    return Pruner(graph=graph, actions=actions)


class TestObservation:
    def test_an_unread_need_becomes_a_candidate(self):
        pruner = wired()
        pruner.observe_run("main.o", {"used.h"})
        candidates = pruner.candidates()
        assert len(candidates) == 1
        assert candidates[0].unused_need == "unused.h"

    def test_a_read_need_is_never_accused(self):
        pruner = wired()
        pruner.observe_run("main.o", {"used.h", "unused.h"})
        assert pruner.candidates() == []

    def test_unobserved_targets_stay_silent(self):
        assert wired().candidates() == []

    def test_observing_a_stranger_is_refused(self):
        with pytest.raises(Invalid):
            wired().observe_run("ghost", set())


class TestPricing:
    def test_wasted_rebuilds_separate_advice_from_meetings(self):
        pruner = wired()
        pruner.observe_run("main.o", {"used.h"})
        quiet = pruner.candidates()[0]
        assert "maybe an ordering constraint" in quiet.line()
        for _ in range(12):
            pruner.record_rebuild("main.o", "unused.h")
        billed = pruner.candidates()[0]
        assert billed.wasted_rebuilds == 12
        assert "worth a meeting" in billed.line()

    def test_the_report_totals_the_bill(self):
        pruner = wired()
        pruner.observe_run("main.o", {"used.h"})
        pruner.record_rebuild("main.o", "unused.h")
        page = pruner.report()
        assert page.endswith("1 suspect edges, 1 wasted rebuilds")

    def test_a_clean_graph_reports_clean(self):
        pruner = wired()
        pruner.observe_run("main.o", {"used.h", "unused.h"})
        assert pruner.report() == "no unused dependencies observed"

    def test_the_worst_billed_edge_leads_the_report(self):
        graph = Graph()
        graph.declare("a.h")
        graph.declare("b.h")
        graph.declare("one.o", needs=("a.h",))
        graph.declare("two.o", needs=("b.h",))
        actions = {
            "one.o": action("one.o", ("a.h",), ("one.o",)),
            "two.o": action("two.o", ("b.h",), ("two.o",)),
        }
        pruner = Pruner(graph=graph, actions=actions)
        pruner.observe_run("one.o", set())
        pruner.observe_run("two.o", set())
        pruner.record_rebuild("two.o", "b.h")
        assert pruner.candidates()[0].target == "two.o"
