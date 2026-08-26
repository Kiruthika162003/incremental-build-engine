"""The parallel scheduler: the critical path is the floor, workers are the walls.

A build's wall-clock floor is its critical path, the most expensive
dependency chain, and no number of workers can dig below it; its
work total is the ceiling one worker pays. The scheduler simulates
the build on a worker pool: a target becomes ready when its needs
finish, ready targets are taken longest-cost-first because saving
the fattest task for last is how a build ends with one worker
grinding while seven watch, and the timeline records who ran what
when. The efficiency line divides ideal speedup by achieved so the
purchase order for more build machines can cite where the curve
bends, and the bend always arrives at the width of the graph, not
at the budget's edge.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid
from forge.graph import Graph


@dataclass(frozen=True)
class Slot:
    target: str
    worker: int
    started: int
    finished: int


@dataclass
class Timeline:
    slots: list[Slot] = field(default_factory=list)
    makespan: int = 0

    def by_worker(self, worker: int) -> list[Slot]:
        return [slot for slot in self.slots if slot.worker == worker]

    def busy_ticks(self) -> int:
        return sum(
            slot.finished - slot.started for slot in self.slots
        )

    def render(self) -> str:
        lines = []
        workers = sorted({slot.worker for slot in self.slots})
        for worker in workers:
            row = " ".join(
                f"{slot.target}[{slot.started}-{slot.finished}]"
                for slot in sorted(
                    self.by_worker(worker), key=lambda s: s.started
                )
            )
            lines.append(f"w{worker}: {row}")
        lines.append(f"makespan {self.makespan}")
        return "\n".join(lines)


@dataclass
class Scheduler:
    graph: Graph
    costs: dict[str, int]

    def _cost(self, name: str) -> int:
        cost = self.costs.get(name, 0)
        if cost < 0:
            raise Invalid(f"{name} has a negative cost")
        return cost

    def critical_path(self, goal: str) -> tuple[int, list[str]]:
        finish: dict[str, int] = {}
        parent: dict[str, str | None] = {}
        for name in self.graph.build_order(goal):
            needs = self.graph.get(name).needs
            best_need = None
            base = 0
            for need in sorted(needs):
                if finish[need] > base:
                    base = finish[need]
                    best_need = need
            finish[name] = base + self._cost(name)
            parent[name] = best_need
        path = []
        cursor: str | None = goal
        while cursor is not None:
            path.append(cursor)
            cursor = parent[cursor]
        return finish[goal], list(reversed(path))

    def total_work(self, goal: str) -> int:
        return sum(
            self._cost(name) for name in self.graph.build_order(goal)
        )

    def simulate(self, goal: str, workers: int) -> Timeline:
        if workers <= 0:
            raise Invalid("a build needs at least one worker")
        order = self.graph.build_order(goal)
        remaining_needs = {
            name: {
                need
                for need in self.graph.get(name).needs
                if need in order
            }
            for name in order
        }
        ready = sorted(
            (name for name, needs in remaining_needs.items() if not needs),
            key=lambda name: (-self._cost(name), name),
        )
        running: list[tuple[int, int, str]] = []
        free_workers = list(range(workers))
        timeline = Timeline()
        now = 0
        done: set[str] = set()
        while len(done) < len(order):
            while ready and free_workers:
                name = ready.pop(0)
                worker = free_workers.pop(0)
                finish = now + self._cost(name)
                running.append((finish, worker, name))
                timeline.slots.append(
                    Slot(
                        target=name,
                        worker=worker,
                        started=now,
                        finished=finish,
                    )
                )
            if not running:
                raise Invalid("nothing running and nothing ready: a hole")
            running.sort()
            finish, worker, name = running.pop(0)
            now = finish
            done.add(name)
            free_workers.append(worker)
            free_workers.sort()
            newly_ready = []
            for other, needs in remaining_needs.items():
                if other in done or other == name:
                    continue
                needs.discard(name)
                if not needs and other not in [
                    slot for _, _, slot in running
                ] and other not in ready:
                    newly_ready.append(other)
            ready.extend(newly_ready)
            ready.sort(key=lambda entry: (-self._cost(entry), entry))
        timeline.makespan = now
        return timeline

    def efficiency(self, goal: str, workers: int) -> str:
        floor, _ = self.critical_path(goal)
        work = self.total_work(goal)
        timeline = self.simulate(goal, workers)
        ideal = max(floor, -(-work // workers))
        achieved = work / (timeline.makespan * workers)
        return (
            f"{workers} workers: makespan {timeline.makespan} against "
            f"a floor of {floor} and an ideal of {ideal}; "
            f"{achieved:.0%} of the pool was busy"
        )
