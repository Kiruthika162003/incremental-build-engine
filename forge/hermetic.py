"""The hermeticity report: a build is trusted action by action, or not at all.

One undeclared read poisons everything downstream of it: the action
key did not include the file, so the cache will happily serve a
stale result the day that file changes. The auditor runs every
action in a build with observation on, grades each against its
declaration, and refuses to bless the build unless every action came
back clean, because hermeticity is not a percentage, it is a
property, and 99 percent hermetic means the cache lies sometimes,
which is worse than a cache that lies always since nobody will
believe the bug report. The gap report names each offender with the
exact paths, sorted by how far the poison spreads, so the fix list
starts with the leak that matters most.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.actions import Action, execute
from forge.engine import Engine
from forge.workspace import Workspace


@dataclass(frozen=True)
class Leak:
    action: str
    undeclared_reads: tuple[str, ...]
    undeclared_writes: tuple[str, ...]
    silent_promises: tuple[str, ...]
    poisoned_downstream: int

    def line(self) -> str:
        parts = []
        if self.undeclared_reads:
            parts.append(f"reads {list(self.undeclared_reads)}")
        if self.undeclared_writes:
            parts.append(f"writes {list(self.undeclared_writes)}")
        if self.silent_promises:
            parts.append(f"never wrote {list(self.silent_promises)}")
        return (
            f"{self.action}: {'; '.join(parts)} "
            f"(poisons {self.poisoned_downstream} downstream)"
        )


@dataclass
class HermeticityReport:
    audited: int = 0
    clean: int = 0
    leaks: list[Leak] = field(default_factory=list)

    def blessed(self) -> bool:
        return self.audited > 0 and not self.leaks

    def page(self) -> str:
        if self.blessed():
            return f"blessed: all {self.audited} actions hermetic"
        lines = [
            f"NOT blessed: {len(self.leaks)} of {self.audited} "
            f"actions leak"
        ]
        for leak in self.leaks:
            lines.append(f"  {leak.line()}")
        return "\n".join(lines)


def audit_build(engine: Engine, goal: str, tree: Workspace) -> HermeticityReport:
    report = HermeticityReport()
    for name in engine.graph.build_order(goal):
        action: Action | None = engine.actions.get(name)
        if action is None:
            continue
        observation = execute(action, tree)
        report.audited += 1
        reads = tuple(observation.undeclared_reads(action))
        writes = tuple(observation.undeclared_writes(action))
        silent = tuple(observation.promised_but_silent(action))
        if not (reads or writes or silent):
            report.clean += 1
            continue
        report.leaks.append(
            Leak(
                action=name,
                undeclared_reads=reads,
                undeclared_writes=writes,
                silent_promises=silent,
                poisoned_downstream=len(
                    engine.graph.downstream_of(name)
                ),
            )
        )
    report.leaks.sort(
        key=lambda leak: (-leak.poisoned_downstream, leak.action)
    )
    return report
