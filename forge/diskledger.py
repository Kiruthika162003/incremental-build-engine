"""The disk ledger: every byte in the output tree answers to a rule.

Build directories grow until the machine files a complaint, and
du tells you which directory is fat without saying which rule to
blame or what is safe to remove. The ledger attributes every
output byte to the rule that wrote it, splits the tree into the
reachable set, bytes some current target still depends on, and
the orphaned set, bytes whose producing rule or consumers are
gone, and the reclaim advice is exactly the orphans because
deleting reachable bytes converts a disk problem into a rebuild
problem. The top-consumers table is per rule, not per directory,
since the fix for a fat rule is in its BUILD file, and the trend
arrow per rule marks growth across snapshots, because the rule
that doubled since last month is more interesting than the rule
that has always been big.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class DiskLedger:
    produced: dict[str, tuple[str, int]] = field(default_factory=dict)
    reachable_targets: set[str] = field(default_factory=set)
    previous_totals: dict[str, int] = field(default_factory=dict)

    def record(self, path: str, rule: str, size: int) -> None:
        if size < 0:
            raise Invalid("bytes cannot be negative")
        self.produced[path] = (rule, size)

    def mark_reachable(self, rules: set[str]) -> None:
        self.reachable_targets = set(rules)

    def _split(self) -> tuple[int, list[tuple[str, int]]]:
        reachable = 0
        orphans = []
        for path, (rule, size) in sorted(self.produced.items()):
            if rule in self.reachable_targets:
                reachable += size
            else:
                orphans.append((path, size))
        return reachable, orphans

    def reclaim_advice(self) -> str:
        reachable, orphans = self._split()
        if not orphans:
            return (
                f"nothing to reclaim; all {reachable} bytes are "
                f"load-bearing"
            )
        freed = sum(size for _, size in orphans)
        names = ", ".join(path for path, _ in orphans)
        return (
            f"reclaim {freed} bytes safely ({names}); the other "
            f"{reachable} are load-bearing and deleting them buys a "
            f"rebuild"
        )

    def top_consumers(self, top: int = 3) -> list[tuple[str, int]]:
        per_rule: dict[str, int] = {}
        for rule, size in self.produced.values():
            per_rule[rule] = per_rule.get(rule, 0) + size
        ranked = sorted(
            per_rule.items(), key=lambda row: (-row[1], row[0])
        )
        return ranked[:top]

    def snapshot(self) -> None:
        totals: dict[str, int] = {}
        for rule, size in self.produced.values():
            totals[rule] = totals.get(rule, 0) + size
        self.previous_totals = totals

    def trends(self) -> list[str]:
        if not self.previous_totals:
            raise Invalid("no snapshot to trend against")
        current: dict[str, int] = {}
        for rule, size in self.produced.values():
            current[rule] = current.get(rule, 0) + size
        moved = []
        for rule in sorted(current):
            then = self.previous_totals.get(rule, 0)
            now = current[rule]
            if then and now >= 2 * then:
                moved.append(
                    f"{rule}: {then} -> {now} bytes; doubled since "
                    f"the snapshot"
                )
        return moved
