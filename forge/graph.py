"""The action graph: what depends on what, with cycles named at the door.

A build is a directed acyclic graph of targets; everything else is
commentary. Each target declares the targets it needs and the rule
that produces it, edges are checked at declaration time so a cycle
is refused with the full loop in the message rather than discovered
as a hang, and the graph answers the three questions every build
tool is really asked: what order can this be built in, what is
downstream of a change, and how wide can the build go at each step.
Topological order breaks ties by name so two runs of the same graph
give one answer, because a build system with moods is a build
system nobody trusts.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Cycle, Invalid, Missing


@dataclass(frozen=True)
class Target:
    name: str
    needs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise Invalid("a target needs a name")
        if self.name in self.needs:
            raise Invalid(f"{self.name} cannot need itself")


@dataclass
class Graph:
    targets: dict[str, Target] = field(default_factory=dict)

    def declare(self, name: str, needs: tuple[str, ...] = ()) -> Target:
        if name in self.targets:
            raise Invalid(f"{name} is already declared")
        target = Target(name=name, needs=needs)
        self.targets[name] = target
        loop = self._find_cycle(name)
        if loop is not None:
            del self.targets[name]
            raise Cycle(" -> ".join(loop))
        return target

    def _find_cycle(self, start: str) -> list[str] | None:
        path: list[str] = []
        seen_on_path: set[str] = set()

        def walk(current: str) -> list[str] | None:
            if current in seen_on_path:
                loop_start = path.index(current)
                return [*path[loop_start:], current]
            if current not in self.targets:
                return None
            path.append(current)
            seen_on_path.add(current)
            for need in self.targets[current].needs:
                found = walk(need)
                if found is not None:
                    return found
            path.pop()
            seen_on_path.discard(current)
            return None

        return walk(start)

    def get(self, name: str) -> Target:
        if name not in self.targets:
            raise Missing(f"no target named {name}")
        return self.targets[name]

    def missing_needs(self) -> dict[str, list[str]]:
        holes: dict[str, list[str]] = {}
        for target in self.targets.values():
            absent = [
                need for need in target.needs if need not in self.targets
            ]
            if absent:
                holes[target.name] = sorted(absent)
        return holes

    def build_order(self, goal: str) -> list[str]:
        """Every target the goal needs, dependencies first, ties by name."""
        self.get(goal)
        ordered: list[str] = []
        placed: set[str] = set()

        def visit(name: str) -> None:
            if name in placed:
                return
            target = self.get(name)
            for need in sorted(target.needs):
                visit(need)
            placed.add(name)
            ordered.append(name)

        visit(goal)
        return ordered

    def downstream_of(self, name: str) -> list[str]:
        """Everything that would go stale if this target changed."""
        self.get(name)
        hit: set[str] = set()
        changed = True
        while changed:
            changed = False
            for target in self.targets.values():
                if target.name in hit:
                    continue
                if any(
                    need == name or need in hit for need in target.needs
                ):
                    hit.add(target.name)
                    changed = True
        return sorted(hit)

    def waves(self, goal: str) -> list[list[str]]:
        """Build order grouped into steps that may run concurrently."""
        depth: dict[str, int] = {}
        for name in self.build_order(goal):
            needs = self.get(name).needs
            depth[name] = (
                0
                if not needs
                else 1 + max(depth[need] for need in needs)
            )
        grouped: dict[int, list[str]] = {}
        for name, level in depth.items():
            grouped.setdefault(level, []).append(name)
        return [sorted(grouped[level]) for level in sorted(grouped)]

    def width(self, goal: str) -> int:
        return max(len(wave) for wave in self.waves(goal))
