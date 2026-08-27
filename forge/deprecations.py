"""Deprecation as a schedule, not a comment: warnings that keep appointments.

A deprecated build attribute with no removal date is not
deprecated, it is renamed forever, because nothing ever forces
the migration. The registry gives each deprecation a lifecycle
measured in observed uses, not calendar time: for the grace
budget it warns with the replacement spelled out, then it
escalates to refusal, and the count is per-attribute across the
whole repo so the loudest offenders surface by arithmetic. The
census is the management view: every deprecation with its
remaining budget and its use count, sorted by how close the
hammer is, so a team can see which migration is about to start
failing builds before it starts failing them, and the one
deprecation nobody has used in the whole window is flagged as
finished, ready for the attribute to be deleted outright.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class Deprecation:
    attribute: str
    replacement: str
    grace_uses: int
    uses_seen: int = 0

    def __post_init__(self) -> None:
        if self.grace_uses < 1:
            raise Invalid(
                f"{self.attribute} needs a positive grace budget; "
                "zero grace is just a removal"
            )
        if self.attribute == self.replacement:
            raise Invalid(
                f"{self.attribute} cannot replace itself"
            )


@dataclass
class DeprecationRegistry:
    entries: dict[str, Deprecation] = field(default_factory=dict)

    def deprecate(
        self, attribute: str, replacement: str, grace_uses: int
    ) -> None:
        if attribute in self.entries:
            raise Invalid(f"{attribute} is already deprecated")
        self.entries[attribute] = Deprecation(
            attribute=attribute,
            replacement=replacement,
            grace_uses=grace_uses,
        )

    def observe(self, attribute: str, target: str) -> str:
        entry = self.entries.get(attribute)
        if entry is None:
            return f"{attribute}: current, carry on"
        entry.uses_seen += 1
        remaining = entry.grace_uses - entry.uses_seen
        if remaining < 0:
            raise Invalid(
                f"{target} uses {attribute}, whose grace budget "
                f"of {entry.grace_uses} is spent; migrate to "
                f"{entry.replacement} to build at all"
            )
        return (
            f"{target}: {attribute} is deprecated, use "
            f"{entry.replacement} ({remaining} grace use(s) left)"
        )

    def census(self) -> str:
        if not self.entries:
            return "no deprecations; the schema is at peace"
        rows = sorted(
            self.entries.values(),
            key=lambda entry: entry.grace_uses - entry.uses_seen,
        )
        lines = [f"{len(rows)} deprecation(s) in flight"]
        for entry in rows:
            remaining = entry.grace_uses - entry.uses_seen
            if entry.uses_seen == 0:
                lines.append(
                    f"  {entry.attribute}: never used in the "
                    "window; delete the attribute outright"
                )
            else:
                lines.append(
                    f"  {entry.attribute} -> {entry.replacement}: "
                    f"{entry.uses_seen} use(s), {remaining} grace "
                    "left"
                )
        return "\n".join(lines)
