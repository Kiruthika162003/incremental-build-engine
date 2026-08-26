from __future__ import annotations

import pytest

from forge.actions import Action
from forge.distexec import Dispatcher, Worker
from forge.errors import Invalid
from forge.workspace import Workspace


def heavy_action(name: str = "compile") -> Action:
    def rule(tree) -> None:
        tree.write_text("out.o", f"obj({tree.read_text('big.c')})")

    return Action(
        name=name,
        command="cc",
        reads=("big.c",),
        writes=("out.o",),
        rule=rule,
    )


def world() -> Workspace:
    tree = Workspace()
    tree.write_text("big.c", "x" * 100)
    return tree


def farm() -> Dispatcher:
    return Dispatcher(
        workers=[Worker(name="w0"), Worker(name="w1")],
        link_bytes_per_tick=10,
    )


class TestDispatch:
    def test_a_fat_action_remotes_and_prices_the_freight(self):
        line = farm().dispatch(heavy_action(), world(), cost=50)
        assert "remoted to w0" in line
        assert "shipped 100 bytes" in line
        assert "saved 40 ticks" in line

    def test_a_cheap_action_is_kept_local_with_the_arithmetic(self):
        dispatcher = farm()
        line = dispatcher.dispatch(heavy_action(), world(), cost=5)
        assert line.startswith("compile: kept local")
        assert "cost 5 <= freight 10" in line
        assert dispatcher.refusals

    def test_the_kept_local_action_still_builds(self):
        tree = world()
        farm().dispatch(heavy_action(), tree, cost=5)
        assert tree.exists("out.o")


class TestAffinity:
    def test_the_second_dispatch_follows_the_bytes(self):
        dispatcher = farm()
        tree = world()
        dispatcher.dispatch(heavy_action("first"), tree, cost=50)
        line = dispatcher.dispatch(heavy_action("second"), tree, cost=50)
        assert "remoted to w0, shipped 0 bytes" in line

    def test_held_inputs_ship_as_nothing(self):
        dispatcher = farm()
        tree = world()
        dispatcher.dispatch(heavy_action("first"), tree, cost=50)
        dispatcher.dispatch(heavy_action("second"), tree, cost=50)
        assert dispatcher.workers[0].bytes_received == 100

    def test_a_zero_freight_action_beats_any_idle_worker(self):
        dispatcher = farm()
        tree = world()
        dispatcher.dispatch(heavy_action("a"), tree, cost=50)
        dispatcher.dispatch(heavy_action("b"), tree, cost=50)
        dispatcher.dispatch(heavy_action("c"), tree, cost=50)
        assert dispatcher.workers[0].actions_run == 3
        assert dispatcher.workers[1].actions_run == 0

    def test_a_warm_farm_makes_cheap_actions_worth_remoting(self):
        dispatcher = farm()
        tree = world()
        dispatcher.dispatch(heavy_action(), tree, cost=50)
        line = dispatcher.dispatch(heavy_action("cheap"), tree, cost=5)
        assert "remoted to w0, shipped 0 bytes" in line

    def test_the_report_reads_the_farm(self):
        dispatcher = farm()
        tree = world()
        dispatcher.dispatch(heavy_action(), tree, cost=50)
        dispatcher.dispatch(heavy_action("cheap"), tree, cost=5)
        page = dispatcher.affinity_report()
        assert "w0: 2 actions, 100 bytes received, 1 objects held" in page
        assert "0 kept local by arithmetic" in page


class TestContracts:
    def test_an_empty_farm_is_refused(self):
        with pytest.raises(Invalid):
            Dispatcher(workers=[])

    def test_a_dead_link_is_refused(self):
        with pytest.raises(Invalid):
            Dispatcher(workers=[Worker(name="w0")], link_bytes_per_tick=0)
