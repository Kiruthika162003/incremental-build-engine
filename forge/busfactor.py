"""Bus factor: the package where one person holds all the keys.

Ownership files say who reviews; edit history says who
understands, and the risk lives in the gap. The census counts
each contributor's share of a package's edits over the window,
and the bus factor is the smallest set of people covering
ninety percent of them: a factor of one means one resignation
letter is an architecture document nobody can read anymore.
The report refuses the two lazy readings: a low factor on a
package nobody edits is dormancy, not danger, flagged
separately, and a high factor achieved by drive-by one-line
commits is thinner than it looks, so the census also prints
the top contributor's share, because "bus factor two" with an
85 percent lead author is a two that behaves like a one. The
prescription is always the same and always printed: the next
two features in this package belong to someone new.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

COVERAGE = 0.9
DORMANT_BELOW = 5


@dataclass
class EditCensus:
    edits: dict[str, dict[str, int]] = field(
        default_factory=dict
    )

    def record(
        self, package: str, author: str, count: int = 1
    ) -> None:
        if count < 1:
            raise Invalid("an edit count below one is not an edit")
        held = self.edits.setdefault(package, {})
        held[author] = held.get(author, 0) + count

    def bus_factor(self, package: str) -> int:
        held = self.edits.get(package)
        if not held:
            raise Invalid(f"{package} has no recorded edits")
        total = sum(held.values())
        covered = 0
        factor = 0
        for count in sorted(held.values(), reverse=True):
            covered += count
            factor += 1
            if covered >= COVERAGE * total:
                return factor
        return factor

    def top_share(self, package: str) -> tuple[str, int]:
        held = self.edits.get(package)
        if not held:
            raise Invalid(f"{package} has no recorded edits")
        total = sum(held.values())
        author = max(held, key=lambda name: held[name])
        return author, 100 * held[author] // total

    def report(self, package: str) -> str:
        held = self.edits.get(package)
        if not held:
            raise Invalid(f"{package} has no recorded edits")
        total = sum(held.values())
        factor = self.bus_factor(package)
        author, share = self.top_share(package)
        if total < DORMANT_BELOW:
            return (
                f"{package}: {total} edit(s) in the window; "
                "dormancy, not danger, and a different review"
            )
        lines = [
            f"{package}: bus factor {factor} over {total} "
            f"edit(s); {author} holds {share}%"
        ]
        if factor == 1:
            lines.append(
                "  a factor of one means one resignation letter "
                "is an architecture document nobody can read"
            )
        elif share >= 80:
            lines.append(
                f"  a factor of {factor} with an {share}% lead "
                "author behaves like a one"
            )
        lines.append(
            "  prescription: the next two features here belong "
            "to someone new"
        )
        return "\n".join(lines)
