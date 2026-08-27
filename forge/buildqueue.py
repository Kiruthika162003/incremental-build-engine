"""The farm's queue: the person waiting outranks the robot that is not.

An interactive build has a human staring at it; a scheduled batch
build has a cron entry. When the farm is full, the queue's whole
job is knowing the difference: interactive requests go to the
front among themselves in arrival order, batch requests wait, and
a batch action already running is preempted only when the ceiling
of waiting humans crosses a threshold, because preemption throws
away work and throwing away work to save seconds is only correct
when the seconds belong to someone. Preempted work is requeued at
the batch front, its progress loss is metered, and the fairness
guard watches the other direction too: a batch job bumped past
its patience budget is promoted to interactive priority, since
"the nightly never finishes" is the failure mode on the far side
of "the human never waits".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

PREEMPT_WHEN_WAITING = 2
PATIENCE_BUMPS = 3


@dataclass
class QueuedBuild:
    name: str
    kind: str
    arrived: int
    bumps: int = 0

    def __post_init__(self) -> None:
        if self.kind not in ("interactive", "batch"):
            raise Invalid(f"unknown kind {self.kind!r}")


@dataclass
class FarmQueue:
    slots: int
    running: dict[str, QueuedBuild] = field(default_factory=dict)
    waiting: list[QueuedBuild] = field(default_factory=list)
    preemptions: int = 0
    work_ticks_lost: int = 0
    promotions: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.slots <= 0:
            raise Invalid("a farm needs slots")

    def submit(self, build: QueuedBuild) -> str:
        if len(self.running) < self.slots:
            self.running[build.name] = build
            return "running"
        if build.kind == "interactive":
            waiting_humans = sum(
                1
                for held in self.waiting
                if held.kind == "interactive"
            ) + 1
            victim = self._batch_victim()
            if (
                victim is not None
                and waiting_humans >= PREEMPT_WHEN_WAITING
            ):
                self._preempt(victim)
                self.running[build.name] = build
                return f"running after preempting {victim.name}"
        self._enqueue(build)
        return "waiting"

    def _batch_victim(self) -> QueuedBuild | None:
        batches = [
            held
            for held in self.running.values()
            if held.kind == "batch"
        ]
        if not batches:
            return None
        return max(batches, key=lambda held: held.arrived)

    def _preempt(self, victim: QueuedBuild, progress: int = 5) -> None:
        del self.running[victim.name]
        victim.bumps += 1
        self.preemptions += 1
        self.work_ticks_lost += progress
        if victim.bumps >= PATIENCE_BUMPS:
            victim = QueuedBuild(
                name=victim.name,
                kind="interactive",
                arrived=victim.arrived,
                bumps=victim.bumps,
            )
            self.promotions.append(victim.name)
        self._enqueue(victim, front_of_class=True)

    def _enqueue(
        self, build: QueuedBuild, front_of_class: bool = False
    ) -> None:
        if front_of_class:
            peers = [
                index
                for index, held in enumerate(self.waiting)
                if held.kind == build.kind
            ]
            position = peers[0] if peers else len(self.waiting)
            self.waiting.insert(position, build)
        else:
            self.waiting.append(build)
        self.waiting.sort(
            key=lambda held: (
                held.kind != "interactive",
                held.arrived,
            )
        )

    def finish(self, name: str) -> str | None:
        if name not in self.running:
            raise Invalid(f"{name} is not running")
        del self.running[name]
        if not self.waiting:
            return None
        promoted = self.waiting.pop(0)
        self.running[promoted.name] = promoted
        return promoted.name

    def bill(self) -> str:
        return (
            f"{self.preemptions} preemptions, "
            f"{self.work_ticks_lost} work ticks thrown away, "
            f"{len(self.promotions)} batch jobs promoted by patience"
        )
