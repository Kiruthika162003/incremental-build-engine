"""Toolchain upgrades: a new compiler is a new world, priced before entry.

Upgrading the compiler invalidates every action whose command
identity embeds it, which in most repositories is a full rebuild
wearing a version bump. The upgrade planner answers the question
before the button is pressed: given the rules and the tool each
command resolves to, how many actions does swapping tool T
invalidate, what do they cost in total, and what fraction of the
cache survives untouched because it never used T. The staged plan
splits the invalidation by graph depth so the rebuild can run as a
rolling wave rather than a cliff, and the receipt names the rules
that dodge the upgrade entirely, because "the linker survives a
compiler bump" is exactly the kind of fact that saves a Friday.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid, Missing
from forge.graph import Graph


@dataclass
class ToolUse:
    rule: str
    tool: str
    cost: int


@dataclass
class UpgradePlanner:
    graph: Graph
    uses: dict[str, ToolUse] = field(default_factory=dict)

    def record(self, rule: str, command: str, cost: int) -> None:
        self.graph.get(rule)
        tool = command.split(maxsplit=1)[0] if command.strip() else ""
        if not tool:
            raise Invalid(f"{rule} has an empty command")
        self.uses[rule] = ToolUse(rule=rule, tool=tool, cost=cost)

    def users_of(self, tool: str) -> list[str]:
        return sorted(
            use.rule for use in self.uses.values() if use.tool == tool
        )

    def invalidation(self, tool: str) -> tuple[int, int, float]:
        """(rules invalidated, ticks to repay, cache survival share)."""
        hit = self.users_of(tool)
        if not hit:
            raise Missing(f"no rule uses {tool}; the upgrade is free")
        ticks = sum(self.uses[rule].cost for rule in hit)
        survival = 1.0 - len(hit) / len(self.uses)
        return len(hit), ticks, round(survival, 4)

    def waves(self, tool: str, goal: str) -> list[list[str]]:
        hit = set(self.users_of(tool))
        depth: dict[str, int] = {}
        for name in self.graph.build_order(goal):
            needs = self.graph.get(name).needs
            depth[name] = (
                0
                if not needs
                else 1 + max(depth.get(need, 0) for need in needs)
            )
        grouped: dict[int, list[str]] = {}
        for rule in hit:
            if rule in depth:
                grouped.setdefault(depth[rule], []).append(rule)
        return [sorted(grouped[level]) for level in sorted(grouped)]

    def survivors(self, tool: str) -> list[str]:
        return sorted(
            use.rule for use in self.uses.values() if use.tool != tool
        )

    def receipt(self, tool: str, goal: str) -> str:
        count, ticks, survival = self.invalidation(tool)
        stages = self.waves(tool, goal)
        lines = [
            f"upgrading {tool}: {count} rules invalidated, "
            f"{ticks} ticks to repay, {survival:.0%} of the cache "
            f"survives",
            f"rolling waves: {len(stages)}",
        ]
        for number, wave in enumerate(stages):
            lines.append(f"  wave {number}: {', '.join(wave)}")
        dodgers = self.survivors(tool)
        if dodgers:
            lines.append(f"untouched: {', '.join(dodgers)}")
        return "\n".join(lines)
