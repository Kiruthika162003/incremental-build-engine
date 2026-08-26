"""Distributed execution: the action travels, and the freight is the fee.

Running an action on a remote worker means shipping every declared
input the worker does not already hold, and the worker's CAS is
the freight discount: inputs it has seen before ship as digests,
not bytes. The dispatcher picks the worker holding the most of the
action's input set, because affinity is worth more than idleness
when the inputs are heavy, and the assignment ledger records what
each choice shipped so the alternative can be priced after the
fact. The break-even line is the module's spine: an action is
worth remoting when its cost exceeds the bytes it must ship over
the effective link speed, and the dispatcher refuses remotes below
the line with the arithmetic in the refusal, since a build farm
that remotes everything spends its speedup on freight.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.actions import Action, execute
from forge.content import digest_bytes
from forge.errors import Invalid
from forge.workspace import Workspace


@dataclass
class Worker:
    name: str
    held: set[str] = field(default_factory=set)
    bytes_received: int = 0
    actions_run: int = 0

    def missing(self, inputs: dict[str, bytes]) -> list[str]:
        return sorted(
            path
            for path, payload in inputs.items()
            if digest_bytes(payload) not in self.held
        )

    def receive(self, inputs: dict[str, bytes]) -> int:
        shipped = 0
        for payload in inputs.values():
            key = digest_bytes(payload)
            if key not in self.held:
                self.held.add(key)
                shipped += len(payload)
        self.bytes_received += shipped
        return shipped


@dataclass
class Dispatcher:
    workers: list[Worker]
    link_bytes_per_tick: int = 10
    shipped_log: list[tuple[str, str, int]] = field(default_factory=list)
    refusals: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.workers:
            raise Invalid("a farm needs workers")
        if self.link_bytes_per_tick <= 0:
            raise Invalid("the link must carry something")

    def _inputs(self, action: Action, tree: Workspace) -> dict[str, bytes]:
        return {path: tree.read(path) for path in action.reads}

    def freight_ticks(self, shipped_bytes: int) -> int:
        return -(-shipped_bytes // self.link_bytes_per_tick)

    def pick_worker(self, action: Action, tree: Workspace) -> Worker:
        inputs = self._inputs(action, tree)
        return min(
            self.workers,
            key=lambda worker: (
                sum(
                    len(inputs[path])
                    for path in worker.missing(inputs)
                ),
                worker.actions_run,
                worker.name,
            ),
        )

    def dispatch(
        self, action: Action, tree: Workspace, cost: int
    ) -> str:
        inputs = self._inputs(action, tree)
        worker = self.pick_worker(action, tree)
        to_ship = sum(
            len(inputs[path]) for path in worker.missing(inputs)
        )
        freight = self.freight_ticks(to_ship)
        if cost <= freight:
            line = (
                f"{action.name}: kept local; cost {cost} <= freight "
                f"{freight} ({to_ship} bytes at "
                f"{self.link_bytes_per_tick}/tick)"
            )
            self.refusals.append(line)
            execute(action, tree)
            return line
        shipped = worker.receive(inputs)
        worker.actions_run += 1
        self.shipped_log.append((action.name, worker.name, shipped))
        execute(action, tree)
        return (
            f"{action.name}: remoted to {worker.name}, shipped "
            f"{shipped} bytes, saved {cost - freight} ticks"
        )

    def affinity_report(self) -> str:
        lines = []
        for worker in self.workers:
            lines.append(
                f"{worker.name}: {worker.actions_run} actions, "
                f"{worker.bytes_received} bytes received, "
                f"{len(worker.held)} objects held"
            )
        lines.append(f"{len(self.refusals)} kept local by arithmetic")
        return "\n".join(lines)
