"""Strict deps: you may use what you declared, not what arrived with it.

A target that needs a library sees that library's own dependencies
on the classpath as a side effect, uses one, and now depends on a
target it never declared: the build works until the intermediary
drops the edge, and then a stranger's cleanup breaks you. Strict
deps closes the loophole: every symbol a rule consumes must trace
to a direct declaration, transitive arrivals are visible but
unusable, and the violation message does the paperwork, naming the
undeclared provider and printing the exact needs line to add. The
unused half is the mirror check: a direct declaration no consumed
symbol traces to is dead weight on the rebuild cone, so the same
pass that catches freeloading also catches hoarding, and the two
lists together are the dependency diet the target actually needs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class Provider:
    target: str
    symbols: tuple[str, ...]


@dataclass
class StrictChecker:
    providers: dict[str, Provider] = field(default_factory=dict)

    def provides(self, target: str, symbols: tuple[str, ...]) -> None:
        if target in self.providers:
            raise Invalid(f"{target} already declares its symbols")
        for symbol in symbols:
            owner = self._owner_of(symbol)
            if owner is not None:
                raise Invalid(
                    f"symbol {symbol} is provided by both {owner} "
                    f"and {target}; one name, one home"
                )
        self.providers[target] = Provider(
            target=target, symbols=symbols
        )

    def _owner_of(self, symbol: str) -> str | None:
        for provider in self.providers.values():
            if symbol in provider.symbols:
                return provider.target
        return None

    def check(
        self,
        target: str,
        declared_deps: tuple[str, ...],
        consumed_symbols: tuple[str, ...],
    ) -> tuple[list[str], list[str]]:
        """Returns (freeloading violations, hoarded declarations)."""
        for dep in declared_deps:
            if dep not in self.providers:
                raise Invalid(
                    f"{target} declares {dep}, which provides nothing"
                )
        violations = []
        used_deps: set[str] = set()
        for symbol in consumed_symbols:
            owner = self._owner_of(symbol)
            if owner is None:
                raise Invalid(
                    f"{target} consumes {symbol}, which nothing "
                    f"provides"
                )
            if owner in declared_deps:
                used_deps.add(owner)
            else:
                violations.append(
                    f"{target} uses {symbol} from {owner} without "
                    f"declaring it; add: needs = {owner}"
                )
        hoarded = [
            f"{target} declares {dep} but consumes nothing from it"
            for dep in declared_deps
            if dep not in used_deps
        ]
        return violations, hoarded

    def diet(
        self,
        target: str,
        declared_deps: tuple[str, ...],
        consumed_symbols: tuple[str, ...],
    ) -> str:
        violations, hoarded = self.check(
            target, declared_deps, consumed_symbols
        )
        if not violations and not hoarded:
            return f"{target}: the declaration matches the diet"
        lines = [*violations, *hoarded]
        return "\n".join(lines)
