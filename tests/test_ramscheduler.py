from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.ramscheduler import MemoryAction, RamScheduler

LINKER = MemoryAction(name="link", ticks=10, peak_ram=9)
COMPILE_A = MemoryAction(name="a.o", ticks=10, peak_ram=2)
COMPILE_B = MemoryAction(name="b.o", ticks=10, peak_ram=2)


class TestTheCeiling:
    def test_everything_fits_when_ram_is_plenty(self):
        scheduler = RamScheduler(workers=4, ram_ceiling=100)
        makespan = scheduler.simulate(
            [LINKER, COMPILE_A, COMPILE_B]
        )
        assert makespan == 10

    def test_two_linkers_cannot_share_sixteen_gigs(self):
        scheduler = RamScheduler(workers=4, ram_ceiling=16)
        second_linker = MemoryAction(
            name="link2", ticks=10, peak_ram=9
        )
        makespan = scheduler.simulate([LINKER, second_linker])
        assert makespan == 20
        assert scheduler.waits_for_memory > 0

    def test_compiles_ride_alongside_one_linker(self):
        scheduler = RamScheduler(workers=4, ram_ceiling=16)
        makespan = scheduler.simulate(
            [LINKER, COMPILE_A, COMPILE_B]
        )
        assert makespan == 10

    def test_the_impossible_action_is_named_not_scheduled(self):
        scheduler = RamScheduler(workers=4, ram_ceiling=8)
        with pytest.raises(Invalid, match="no schedule fixes"):
            scheduler.simulate([LINKER])

    def test_nonsense_machines_are_refused(self):
        with pytest.raises(Invalid):
            RamScheduler(workers=0, ram_ceiling=16)


class TestDiagnosis:
    def test_the_memory_bound_build_says_buy_ram(self):
        scheduler = RamScheduler(workers=8, ram_ceiling=16)
        linkers = [
            MemoryAction(name=f"link{n}", ticks=10, peak_ram=9)
            for n in range(4)
        ]
        scheduler.simulate(linkers)
        assert scheduler.diagnosis().startswith("memory-bound")

    def test_the_worker_bound_build_says_buy_workers(self):
        scheduler = RamScheduler(workers=1, ram_ceiling=100)
        compiles = [
            MemoryAction(name=f"c{n}.o", ticks=5, peak_ram=1)
            for n in range(4)
        ]
        scheduler.simulate(compiles)
        assert scheduler.diagnosis().startswith("worker-bound")

    def test_a_fitting_machine_reads_balanced(self):
        scheduler = RamScheduler(workers=4, ram_ceiling=100)
        scheduler.simulate([COMPILE_A, COMPILE_B])
        assert scheduler.diagnosis() == (
            "balanced waits; the machine fits the build"
        )
