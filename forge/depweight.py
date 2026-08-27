"""Dependency weight: the forty percent of the binary that is one library.

Binaries gain weight in other people's code, and the diet
starts with a scale, not an opinion: each dependency's
contribution to the shipped closure is measured in bytes, the
report ranks them, and the what-if column answers the only
question the meeting will ask, what do we get back if this one
goes. The subtlety the scale must respect is sharing: a
library kept alive by three dependents is not reclaimed by
removing one of them, so the what-if for a single edge is
often zero bytes, and printing that zero honestly is the
module's best moment, because teams routinely delete a
dependency, measure no shrinkage, and conclude the scale is
broken when the graph was simply telling them about the other
two roads into the same code.

The first test guessed proto would lead the table at 74
percent; the measured table puts netlib first at 88, because a
row's weight is its closure and netlib's closure carries proto
inside it. Closure weights double-count shared code across
rows, shares can sum past 100 percent, and the ranking answers
"which door carries the most bytes", not "which bytes are
unique to this door"; the what-if column is the one that
answers uniqueness, and the two columns disagreeing is the
table teaching, not failing.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid


@dataclass
class WeightScale:
    sizes: dict[str, int]
    needs: dict[str, tuple[str, ...]]

    def closure(self, root: str) -> set[str]:
        if root not in self.sizes:
            raise Invalid(f"{root} is not on the scale")
        seen: set[str] = set()
        frontier = [root]
        while frontier:
            current = frontier.pop()
            if current in seen:
                continue
            seen.add(current)
            frontier.extend(self.needs.get(current, ()))
        return seen

    def shipped_bytes(self, root: str) -> int:
        return sum(
            self.sizes[name] for name in self.closure(root)
        )

    def what_if_removed(
        self, root: str, dropped_edge: str
    ) -> int:
        held = self.needs.get(root, ())
        if dropped_edge not in held:
            raise Invalid(
                f"{root} does not depend on {dropped_edge}"
            )
        trimmed = WeightScale(
            sizes=self.sizes,
            needs={
                **self.needs,
                root: tuple(
                    need
                    for need in held
                    if need != dropped_edge
                ),
            },
        )
        return self.shipped_bytes(root) - trimmed.shipped_bytes(
            root
        )

    def diet_report(self, root: str) -> str:
        total = self.shipped_bytes(root)
        rows = []
        for need in sorted(self.needs.get(root, ())):
            reclaimed = self.what_if_removed(root, need)
            weight = self.shipped_bytes(need)
            rows.append((weight, need, reclaimed))
        rows.sort(reverse=True)
        lines = [f"{root} ships {total} byte(s)"]
        for weight, need, reclaimed in rows:
            share = 100 * weight // total
            note = (
                f"reclaims {reclaimed}"
                if reclaimed
                else "reclaims 0: other roads reach the same "
                "code, and this zero is the scale working"
            )
            lines.append(
                f"  {need}: {weight} byte(s) ({share}%); "
                f"dropping the edge {note}"
            )
        return "\n".join(lines)
