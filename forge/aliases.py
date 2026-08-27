"""Target renames: the old name forwards, complains, and then expires.

Renaming a target with fifty dependents cannot land as one atomic
commit across ten teams, so the rename ships as an alias: the old
name resolves to the new target, every resolution through it is
counted per caller, and the alias carries an expiry. Before the
deadline the alias works and nags, listing its remaining callers
so the migration has a worklist instead of a feeling; after the
deadline it fails with the new name in the message, which converts
the stragglers' problem from silent to five-second. Chained
aliases are refused at declaration, old pointing to older pointing
to oldest, because alias chains are how a rename becomes
archaeology, and an alias to a target that does not exist is
refused for the same reason a broken signpost is worse than no
signpost.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid, Missing, Stale
from forge.graph import Graph


@dataclass
class Alias:
    old: str
    new: str
    expires: int
    callers: dict[str, int] = field(default_factory=dict)


@dataclass
class AliasBook:
    graph: Graph
    aliases: dict[str, Alias] = field(default_factory=dict)

    def declare(self, old: str, new: str, expires: int) -> None:
        if old in self.aliases:
            raise Invalid(f"{old} is already an alias")
        if new in self.aliases:
            raise Invalid(
                f"{new} is itself an alias; chains are archaeology"
            )
        if new not in self.graph.targets:
            raise Missing(
                f"{old} would point at {new}, which does not exist; "
                f"a broken signpost is worse than none"
            )
        self.aliases[old] = Alias(old=old, new=new, expires=expires)

    def resolve(self, name: str, caller: str, now: int) -> str:
        held = self.aliases.get(name)
        if held is None:
            return name
        if now >= held.expires:
            raise Stale(
                f"{name} expired at {held.expires}; the target is "
                f"called {held.new} now"
            )
        held.callers[caller] = held.callers.get(caller, 0) + 1
        return held.new

    def worklist(self, now: int) -> str:
        if not self.aliases:
            return "no aliases; every name is a real name"
        lines = []
        for old in sorted(self.aliases):
            held = self.aliases[old]
            remaining = held.expires - now
            state = (
                f"{remaining} ticks left"
                if remaining > 0
                else "EXPIRED"
            )
            callers = (
                ", ".join(
                    f"{caller} ({count}x)"
                    for caller, count in sorted(held.callers.items())
                )
                or "nobody yet"
            )
            lines.append(
                f"{old} -> {held.new} [{state}]: {callers}"
            )
        return "\n".join(lines)

    def safe_to_delete(self, now: int) -> list[str]:
        """Expired aliases nobody resolved in their final period."""
        return sorted(
            old
            for old, held in self.aliases.items()
            if now >= held.expires and not held.callers
        )
