"""Dead exports: a public face nobody looks at is churn waiting to happen.

Every public symbol is a promise that widens the interface
digest, and a promise nobody consumes is pure liability: it
ripples rebuilds when it moves and binds the author to
compatibility nobody is using. The census crosses the exports of
each unit with the imports of every other unit and names the
exports with zero consumers, each with its shrink-to-private
recommendation and the rebuild cone it would stop dragging. The
exception list is part of the design, not an afterthought:
entry points, plugin hooks, and public API surfaces are consumed
from outside the graph the census can see, so they are declared
exempt with a reason, and an exemption without a reason is
refused, because "probably used somewhere" is how dead exports
got this old in the first place.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class ExportCensus:
    exports: dict[str, tuple[str, ...]] = field(
        default_factory=dict
    )
    imports: dict[str, tuple[tuple[str, str], ...]] = field(
        default_factory=dict
    )
    exemptions: dict[tuple[str, str], str] = field(
        default_factory=dict
    )
    dependents: dict[str, int] = field(default_factory=dict)

    def declare_unit(
        self,
        unit: str,
        exports: tuple[str, ...],
        imports: tuple[tuple[str, str], ...] = (),
        dependent_count: int = 0,
    ) -> None:
        if unit in self.exports:
            raise Invalid(f"{unit} already declared")
        self.exports[unit] = tuple(exports)
        self.imports[unit] = tuple(imports)
        self.dependents[unit] = dependent_count

    def exempt(
        self, unit: str, symbol: str, reason: str
    ) -> None:
        if not reason.strip():
            raise Invalid(
                f"{unit}.{symbol}: probably-used-somewhere is "
                "how dead exports get old; write the reason"
            )
        self.exemptions[(unit, symbol)] = reason

    def _consumed(self) -> set[tuple[str, str]]:
        used = set()
        for imported in self.imports.values():
            used.update(imported)
        return used

    def dead(self) -> list[str]:
        used = self._consumed()
        found = []
        for unit in sorted(self.exports):
            for symbol in self.exports[unit]:
                if (unit, symbol) in used:
                    continue
                if (unit, symbol) in self.exemptions:
                    continue
                cone = self.dependents[unit]
                found.append(
                    f"{unit}.{symbol}: no consumer; make it "
                    f"private and stop dragging {cone} "
                    "dependent(s) when it moves"
                )
        return found

    def report(self) -> str:
        findings = self.dead()
        exempt_lines = [
            f"  exempt {unit}.{symbol}: {reason}"
            for (unit, symbol), reason in sorted(
                self.exemptions.items()
            )
        ]
        if not findings:
            head = "every export has a consumer or a reason"
        else:
            head = f"{len(findings)} dead export(s)"
        return "\n".join(
            [head]
            + [f"  {finding}" for finding in findings]
            + exempt_lines
        )
