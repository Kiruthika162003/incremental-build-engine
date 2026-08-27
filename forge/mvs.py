"""Minimal version selection: the build picks the oldest that satisfies.

Range resolvers pick the newest allowed version, which means a
stranger's release last night changes what you build today. MVS
inverts the bet: every module states the minimum version of each
dependency it needs, the selection for the whole build is the
maximum of the minimums, and nothing else is consulted, so the
answer is a pure function of the requirement graph with no
registry timestamps in it. The diamond resolves without a fight:
two modules wanting v1.2 and v1.4 of the same library get v1.4,
the smallest version satisfying both, and the upgrade story is
explicit: a build's selection moves only when someone edits a
requirement, and the blame line for any selected version names
the requirement that forced it, which turns "why are we on 1.4"
from an investigation into a lookup.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid, Missing


@dataclass
class Module:
    name: str
    requires: dict[str, tuple[int, int]] = field(default_factory=dict)


@dataclass
class Universe:
    modules: dict[str, Module] = field(default_factory=dict)

    def declare(
        self,
        name: str,
        requires: dict[str, tuple[int, int]] | None = None,
    ) -> None:
        if name in self.modules:
            raise Invalid(f"{name} is already declared")
        self.modules[name] = Module(
            name=name, requires=dict(requires or {})
        )

    def select(self, root: str) -> dict[str, tuple[int, int]]:
        if root not in self.modules:
            raise Missing(f"no module named {root}")
        selected: dict[str, tuple[int, int]] = {}
        frontier = [root]
        seen = {root}
        while frontier:
            current = frontier.pop(0)
            module = self.modules[current]
            for dep, minimum in sorted(module.requires.items()):
                if dep not in self.modules:
                    raise Missing(
                        f"{current} requires {dep}, which does not "
                        f"exist"
                    )
                held = selected.get(dep)
                if held is None or minimum > held:
                    selected[dep] = minimum
                if dep not in seen:
                    seen.add(dep)
                    frontier.append(dep)
        return selected

    def blame(self, root: str, dep: str) -> str:
        selection = self.select(root)
        if dep not in selection:
            raise Missing(f"{dep} is not in {root}'s selection")
        chosen = selection[dep]
        claimants = sorted(
            name
            for name, module in self.modules.items()
            if module.requires.get(dep) == chosen
        )
        return (
            f"{dep} {chosen} was forced by {', '.join(claimants)}; "
            f"every other requirement wanted the same or older"
        )

    def upgrade_delta(
        self, root: str, module: str, dep: str, new_minimum: tuple[int, int]
    ) -> list[str]:
        before = self.select(root)
        held = self.modules[module].requires.get(dep)
        if held is None:
            raise Invalid(f"{module} does not require {dep}")
        self.modules[module].requires[dep] = new_minimum
        after = self.select(root)
        self.modules[module].requires[dep] = held
        moved = [
            f"{name}: {before[name]} -> {after[name]}"
            for name in sorted(after)
            if before.get(name) != after[name]
        ]
        return moved or ["nothing moves; the edit is absorbed"]
