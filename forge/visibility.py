"""Visibility: a dependency is a request, and the owner may say no.

Nothing in a monorepo stops one team from depending on another
team's internals except a rule the build system enforces, and the
day that rule is missing, every helper function becomes a public
API with fifty callers and no contract. Targets live in packages,
visibility is declared per target: private to its package, open to
a named list of packages, or public, with private the default
because accidental publicity is the disease and deliberate
publicity the cure. The checker walks every edge and refuses the
graph if any crosses a wall, naming both sides and the missing
grant, and the widen advice is mechanical: the exact declaration
the owner would add if they mean to allow it, so the conversation
starts from a diff instead of a debate.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid
from forge.graph import Graph


@dataclass(frozen=True)
class Visibility:
    kind: str
    allowed: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in ("private", "restricted", "public"):
            raise Invalid(f"unknown visibility {self.kind!r}")
        if self.kind == "restricted" and not self.allowed:
            raise Invalid(
                "restricted visibility needs at least one package"
            )


PRIVATE = Visibility(kind="private")
PUBLIC = Visibility(kind="public")


def package_of(target: str) -> str:
    if "/" not in target:
        return ""
    return target.rsplit("/", 1)[0]


@dataclass
class VisibilityWall:
    graph: Graph
    declared: dict[str, Visibility] = field(default_factory=dict)

    def declare(self, target: str, visibility: Visibility) -> None:
        self.graph.get(target)
        self.declared[target] = visibility

    def _of(self, target: str) -> Visibility:
        return self.declared.get(target, PRIVATE)

    def may_depend(self, user: str, used: str) -> bool:
        visibility = self._of(used)
        if visibility.kind == "public":
            return True
        user_package = package_of(user)
        used_package = package_of(used)
        if user_package == used_package:
            return True
        if visibility.kind == "restricted":
            return user_package in visibility.allowed
        return False

    def violations(self) -> list[str]:
        found = []
        for target in sorted(self.graph.targets):
            for need in sorted(self.graph.get(target).needs):
                if need not in self.graph.targets:
                    continue
                if not self.may_depend(target, need):
                    found.append(
                        f"{target} may not see {need} "
                        f"({self._of(need).kind} to "
                        f"{package_of(need) or 'the root'}); "
                        f"grant: {self.widen_advice(target, need)}"
                    )
        return found

    def widen_advice(self, user: str, used: str) -> str:
        current = self._of(used)
        user_package = package_of(user)
        if current.kind == "restricted":
            grown = (*current.allowed, user_package)
            return (
                f"declare {used} restricted to "
                f"{sorted(set(grown))}"
            )
        return f"declare {used} restricted to ['{user_package}']"

    def assert_walled(self) -> None:
        found = self.violations()
        if found:
            raise Invalid("\n".join(found))
