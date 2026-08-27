"""Draining a worker: finish what you hold, take nothing new, hand off warm.

Maintenance wants the machine now; the machine holds three
running actions and a warm persistent compiler. Kill it and
three builds fail for a reboot's convenience; wait for idle and
maintenance waits forever on a busy farm. The drain is the
contract between those failures: the worker stops accepting,
finishes what it holds with a deadline, and hands its warm
state to a named successor before going down, so the fleet
loses a machine without losing the machine's accumulated
usefulness. The deadline has teeth, an action still running
when it expires is requeued elsewhere with its eviction named,
and the drain report is written for the maintenance ticket:
what finished, what moved, what warmth was handed to whom,
because "the worker was drained" should be a checkable claim,
not a hope with a timestamp.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class DrainingWorker:
    name: str
    running: dict[str, int]
    warm_state: tuple[str, ...] = ()
    draining: bool = False
    finished: list[str] = field(default_factory=list)
    evicted: list[str] = field(default_factory=list)
    handoff: str | None = None

    def accept(self, action: str) -> str:
        if self.draining:
            raise Invalid(
                f"{self.name} is draining and accepts nothing "
                "new; that is the entire meaning of draining"
            )
        self.running[action] = self.running.get(action, 0)
        return f"{action} accepted"

    def begin_drain(self, deadline_ticks: int) -> str:
        if self.draining:
            raise Invalid(f"{self.name} is already draining")
        if deadline_ticks <= 0:
            raise Invalid(
                "a zero deadline is a kill wearing a drain's "
                "name"
            )
        self.draining = True
        self.deadline = deadline_ticks
        return (
            f"{self.name} draining: {len(self.running)} "
            f"action(s) get {deadline_ticks} tick(s) to finish"
        )

    def run_out(self) -> None:
        if not self.draining:
            raise Invalid("drain first")
        for action, ticks_left in sorted(self.running.items()):
            if ticks_left <= self.deadline:
                self.finished.append(action)
            else:
                self.evicted.append(
                    f"{action} requeued elsewhere: needed "
                    f"{ticks_left} against a deadline of "
                    f"{self.deadline}"
                )
        self.running.clear()

    def hand_off(self, successor: str) -> str:
        if self.running:
            raise Invalid(
                "hand off after the deadline, not during"
            )
        if not self.warm_state:
            self.handoff = successor
            return f"nothing warm to hand {successor}"
        self.handoff = successor
        return (
            f"{', '.join(self.warm_state)} handed to "
            f"{successor}; the fleet loses a machine, not the "
            "machine's accumulated usefulness"
        )

    def ticket_report(self) -> str:
        if self.handoff is None:
            raise Invalid("the drain is not finished")
        lines = [
            f"{self.name} drained: {len(self.finished)} "
            f"finished, {len(self.evicted)} evicted, warmth "
            f"to {self.handoff}"
        ]
        lines.extend(f"  {entry}" for entry in self.evicted)
        return "\n".join(lines)
