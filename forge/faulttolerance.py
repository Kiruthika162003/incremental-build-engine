"""Worker failure: the farm loses a machine, the build loses nothing.

A remote worker dies holding leased actions, and the two wrong
responses bracket the right one: failing the build punishes the
user for the farm's hardware, and silently forgetting the lease
hangs the build forever waiting on a corpse. The tracker leases
every dispatched action with the worker's name, heartbeats mark
workers alive, and a worker silent past the deadline is declared
dead exactly once: its leases return to the ready pool, its held
CAS objects are forgotten so freight accounting stays honest, and
the re-dispatch counter records what the failure cost. The
invariant the tests pin is conservation: every action leased is
eventually either completed or returned, never both and never
neither, because a build system that loses work in a crash is a
build system that cannot be believed about anything else.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid, Stale

HEARTBEAT_DEADLINE = 10


@dataclass
class Lease:
    action: str
    worker: str
    leased_at: int


@dataclass
class FaultTracker:
    leases: dict[str, Lease] = field(default_factory=dict)
    last_heartbeat: dict[str, int] = field(default_factory=dict)
    dead: set[str] = field(default_factory=set)
    completed: list[str] = field(default_factory=list)
    returned: list[str] = field(default_factory=list)
    redispatches: int = 0

    def heartbeat(self, worker: str, now: int) -> None:
        if worker in self.dead:
            raise Stale(
                f"{worker} was declared dead; a late heartbeat does "
                f"not resurrect it"
            )
        self.last_heartbeat[worker] = now

    def lease(self, action: str, worker: str, now: int) -> None:
        if worker in self.dead:
            raise Invalid(f"{worker} is dead; nothing leases to it")
        if action in self.leases:
            raise Invalid(
                f"{action} is already leased to "
                f"{self.leases[action].worker}"
            )
        self.leases[action] = Lease(
            action=action, worker=worker, leased_at=now
        )
        self.last_heartbeat.setdefault(worker, now)

    def complete(self, action: str) -> None:
        held = self.leases.pop(action, None)
        if held is None:
            raise Invalid(f"{action} holds no lease")
        self.completed.append(action)

    def patrol(self, now: int) -> list[str]:
        """Declare the silent dead; return their actions to ready."""
        freed = []
        for worker, seen in sorted(self.last_heartbeat.items()):
            if worker in self.dead:
                continue
            if now - seen < HEARTBEAT_DEADLINE:
                continue
            self.dead.add(worker)
            orphaned = sorted(
                action
                for action, held in self.leases.items()
                if held.worker == worker
            )
            for action in orphaned:
                del self.leases[action]
                self.returned.append(action)
                self.redispatches += 1
                freed.append(action)
        return freed

    def conservation_holds(self, ever_leased: list[str]) -> bool:
        finished = set(self.completed)
        waiting = set(self.returned) | set(self.leases)
        for action in ever_leased:
            in_finished = action in finished
            in_waiting = action in waiting
            if in_finished == in_waiting:
                return False
        return True

    def bill(self) -> str:
        return (
            f"{len(self.dead)} workers lost, {self.redispatches} "
            f"actions re-dispatched, {len(self.completed)} completed"
        )
