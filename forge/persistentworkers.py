"""Persistent workers: the compiler that stays warm answers faster.

Some tools pay a startup toll on every invocation, a JVM booting
or a model of headers being reparsed, and cold-starting them per
action spends most of the build inside the same prologue. A
persistent worker boots once, keeps its state warm, and answers
requests for its tool at marginal cost; the pool leases workers by
tool, boots one only when no warm worker is free, and retires the
idlest when the pool is over budget. The economics are explicit:
every request records whether it paid the boot toll or rode a warm
worker, and the amortisation line divides the tolls actually paid
by the requests served, since the difference between one boot per
build and one boot per action is the entire reason this pattern
exists. Warm state is also a risk, so a worker answers a bounded
number of requests before mandatory retirement, because a daemon
that drifts serves subtly stale answers with total confidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

REQUESTS_BEFORE_RETIREMENT = 100


@dataclass
class WarmWorker:
    tool: str
    boot_cost: int
    served: int = 0
    busy: bool = False


@dataclass
class WorkerPool:
    boot_costs: dict[str, int]
    budget: int = 4
    workers: list[WarmWorker] = field(default_factory=list)
    tolls_paid: int = 0
    requests: int = 0
    retirements: int = 0

    def __post_init__(self) -> None:
        if self.budget <= 0:
            raise Invalid("a pool needs a budget of at least one")

    def _boot(self, tool: str) -> WarmWorker:
        if tool not in self.boot_costs:
            raise Invalid(f"no boot cost is known for {tool}")
        if len(self.workers) >= self.budget:
            idlest = max(
                (
                    worker
                    for worker in self.workers
                    if not worker.busy
                ),
                key=lambda worker: worker.served,
                default=None,
            )
            if idlest is None:
                raise Invalid(
                    "the pool is full and everyone is busy; raise the "
                    "budget or wait"
                )
            self.workers.remove(idlest)
            self.retirements += 1
        worker = WarmWorker(tool=tool, boot_cost=self.boot_costs[tool])
        self.workers.append(worker)
        self.tolls_paid += worker.boot_cost
        return worker

    def request(self, tool: str) -> tuple[str, int]:
        """Returns ('warm'|'booted', cost of servicing)."""
        self.requests += 1
        warm = next(
            (
                worker
                for worker in self.workers
                if worker.tool == tool and not worker.busy
            ),
            None,
        )
        if warm is not None:
            warm.served += 1
            if warm.served >= REQUESTS_BEFORE_RETIREMENT:
                self.workers.remove(warm)
                self.retirements += 1
            return "warm", 1
        worker = self._boot(tool)
        worker.served += 1
        return "booted", worker.boot_cost + 1

    def amortisation(self) -> str:
        if self.requests == 0:
            raise Invalid("no requests yet; nothing to amortise")
        return (
            f"{self.tolls_paid} ticks of boot toll over "
            f"{self.requests} requests "
            f"({round(self.tolls_paid / self.requests, 2)} per request), "
            f"{self.retirements} retirements"
        )
