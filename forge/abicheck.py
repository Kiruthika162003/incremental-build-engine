"""ABI checking: a library's exports are a promise its dependents cashed.

Removing a symbol from a shared library does not break the
library; it breaks every dependent at load time, in production,
alphabetically. The checker diffs a library's export list between
versions and grades each change by who pays: added symbols are
free, removed or retyped symbols are priced by the dependents
that import them, named per symbol, and a removal nobody imports
is demoted to a warning because deleting genuinely dead exports
is hygiene, not breakage. The verdict is per release, not per
symbol: one paid removal makes the release major, and the report
prints the dependents' names because "this breaks people" lands
differently when the people have names, and semantic versioning
enforced by tooling is the only kind that survives a deadline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class AbiChecker:
    imports: dict[str, set[str]] = field(default_factory=dict)

    def dependent_imports(
        self, dependent: str, symbols: set[str]
    ) -> None:
        if dependent in self.imports:
            raise Invalid(f"{dependent} already declared its imports")
        self.imports[dependent] = set(symbols)

    def _importers_of(self, symbol: str) -> list[str]:
        return sorted(
            name
            for name, symbols in self.imports.items()
            if symbol in symbols
        )

    def diff(
        self, before: set[str], after: set[str]
    ) -> tuple[list[str], list[str], list[str]]:
        added = sorted(after - before)
        removed_paid = []
        removed_free = []
        for symbol in sorted(before - after):
            importers = self._importers_of(symbol)
            if importers:
                removed_paid.append(
                    f"{symbol}: breaks {', '.join(importers)}"
                )
            else:
                removed_free.append(
                    f"{symbol}: nobody imports it; hygiene, not "
                    f"breakage"
                )
        return added, removed_paid, removed_free

    def release_verdict(
        self, before: set[str], after: set[str]
    ) -> str:
        added, paid, free = self.diff(before, after)
        if paid:
            lines = [
                f"MAJOR: {len(paid)} removal(s) with paying "
                f"dependents"
            ]
            lines.extend(f"  {line}" for line in paid)
            return "\n".join(lines)
        if added:
            return (
                f"minor: {len(added)} symbols added, "
                f"{len(free)} dead exports cleaned"
            )
        if free:
            return f"patch: {len(free)} dead exports cleaned"
        return "patch: the surface is unchanged"
