"""Memory-aware scheduling: parallelism ends where the RAM does.

Eight workers mean nothing if three linkers at nine gigabytes
each land together on a sixteen-gigabyte machine: the OS starts
swapping and the build enters a slowness no profiler explains.
The scheduler treats memory as a second resource: every action
declares its peak, the concurrent set must fit the machine, and a
ready action that would breach the ceiling waits even while
workers idle, which is the correct waste because an idle worker
costs a slot while a swapping machine costs the whole fleet's
sanity. The report separates the two waits, blocked-on-workers
and blocked-on-memory, since the first is solved by buying
workers and the second by buying RAM or splitting the linker, and
a team that cannot tell them apart buys the wrong thing.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid


@dataclass(frozen=True)
class MemoryAction:
    name: str
    ticks: int
    peak_ram: int


@dataclass
class RamScheduler:
    workers: int
    ram_ceiling: int
    waits_for_workers: int = 0
    waits_for_memory: int = 0

    def __post_init__(self) -> None:
        if self.workers <= 0 or self.ram_ceiling <= 0:
            raise Invalid("workers and RAM must be positive")

    def simulate(self, actions: list[MemoryAction]) -> int:
        for action in actions:
            if action.peak_ram > self.ram_ceiling:
                raise Invalid(
                    f"{action.name} alone needs {action.peak_ram} "
                    f"against a ceiling of {self.ram_ceiling}; no "
                    f"schedule fixes that"
                )
        pending = sorted(
            actions, key=lambda held: (-held.peak_ram, held.name)
        )
        running: list[tuple[int, MemoryAction]] = []
        now = 0
        while pending or running:
            ram_used = sum(
                action.peak_ram for _, action in running
            )
            started = True
            while started and pending:
                started = False
                for index, action in enumerate(pending):
                    if len(running) >= self.workers:
                        self.waits_for_workers += 1
                        break
                    if ram_used + action.peak_ram > self.ram_ceiling:
                        self.waits_for_memory += 1
                        continue
                    running.append((now + action.ticks, action))
                    ram_used += action.peak_ram
                    pending.pop(index)
                    started = True
                    break
            if not running:
                raise Invalid("deadlock: nothing fits and nothing runs")
            running.sort(key=lambda held: held[0])
            finish, _ = running.pop(0)
            now = finish
        return now

    def diagnosis(self) -> str:
        if self.waits_for_memory > self.waits_for_workers:
            return (
                f"memory-bound ({self.waits_for_memory} memory waits "
                f"vs {self.waits_for_workers} worker waits): buy RAM "
                f"or split the linker"
            )
        if self.waits_for_workers > self.waits_for_memory:
            return (
                f"worker-bound ({self.waits_for_workers} worker "
                f"waits vs {self.waits_for_memory} memory waits): "
                f"buy workers"
            )
        return "balanced waits; the machine fits the build"
