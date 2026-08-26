from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.graph import Graph
from forge.scheduler import Scheduler


def wide_build() -> Scheduler:
    graph = Graph()
    graph.declare("gen")
    for number in range(4):
        graph.declare(f"obj{number}", needs=("gen",))
    graph.declare(
        "app", needs=tuple(f"obj{number}" for number in range(4))
    )
    costs = {"gen": 2, "app": 3}
    costs.update({f"obj{number}": 4 for number in range(4)})
    return Scheduler(graph=graph, costs=costs)


class TestTheFloor:
    def test_the_critical_path_is_the_fattest_chain(self):
        floor, path = wide_build().critical_path("app")
        assert floor == 9
        assert path[0] == "gen"
        assert path[-1] == "app"
        assert len(path) == 3

    def test_total_work_is_the_one_worker_ceiling(self):
        assert wide_build().total_work("app") == 21

    def test_negative_costs_are_refused(self):
        build = wide_build()
        build.costs["gen"] = -1
        with pytest.raises(Invalid):
            build.critical_path("app")


class TestSimulation:
    def test_one_worker_pays_the_full_ceiling(self):
        timeline = wide_build().simulate("app", workers=1)
        assert timeline.makespan == 21

    def test_four_workers_land_on_the_floor(self):
        timeline = wide_build().simulate("app", workers=4)
        assert timeline.makespan == 9

    def test_more_workers_than_width_buy_nothing(self):
        four = wide_build().simulate("app", workers=4).makespan
        eight = wide_build().simulate("app", workers=8).makespan
        assert four == eight

    def test_two_workers_split_the_middle_wave(self):
        timeline = wide_build().simulate("app", workers=2)
        assert timeline.makespan == 13

    def test_the_pool_is_never_idle_while_work_is_ready(self):
        timeline = wide_build().simulate("app", workers=2)
        assert timeline.busy_ticks() == 21

    def test_zero_workers_are_refused(self):
        with pytest.raises(Invalid):
            wide_build().simulate("app", workers=0)

    def test_the_timeline_renders_per_worker(self):
        page = wide_build().simulate("app", workers=1).render()
        assert page.startswith("w0: gen[0-2]")
        assert page.endswith("makespan 21")


class TestEfficiency:
    def test_the_line_cites_floor_ideal_and_busyness(self):
        line = wide_build().efficiency("app", workers=4)
        assert line == (
            "4 workers: makespan 9 against a floor of 9 and an ideal "
            "of 9; 58% of the pool was busy"
        )
