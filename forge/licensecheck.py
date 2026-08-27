"""License propagation: the lawyer's first question is how did that get in.

Licenses ride the dependency graph whether the graph admits it or
not: a permissive leaf is free to link anywhere, a copyleft
library claims every binary that links it, and a notice license
quietly obliges the shipping artifact to carry an attribution.
The checker walks each shipping target's closure, applies the
policy the target declared, and reports violations as paths, not
verdicts, because "app depends on gpl-lib" starts an argument
while "app -> network -> tlswrap (copyleft)" starts a fix: the
path names the edge to cut or the policy to change. The NOTICE
builder is the same walk with a different pen, collecting every
attribution obligation in the closure exactly once, sorted,
because a NOTICE file assembled by hand is a NOTICE file that is
wrong by the second release.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid, Missing

PERMISSIVE = "permissive"
NOTICE = "notice"
COPYLEFT = "copyleft"
KINDS = (PERMISSIVE, NOTICE, COPYLEFT)


@dataclass(frozen=True)
class License:
    name: str
    kind: str
    attribution: str = ""

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise Invalid(
                f"license kind {self.kind} is not one of {KINDS}"
            )
        if self.kind == NOTICE and not self.attribution:
            raise Invalid(
                f"{self.name} is a notice license and must carry "
                "its attribution text"
            )


@dataclass
class LicenseGraph:
    licenses: dict[str, License] = field(default_factory=dict)
    needs: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def declare(
        self,
        target: str,
        license: License,
        needs: tuple[str, ...] = (),
    ) -> None:
        if target in self.licenses:
            raise Invalid(f"{target} already declared")
        self.licenses[target] = license
        self.needs[target] = tuple(needs)

    def closure(self, target: str) -> list[str]:
        if target not in self.licenses:
            raise Missing(f"{target} is not declared")
        seen: list[str] = []
        frontier = [target]
        while frontier:
            current = frontier.pop(0)
            if current in seen:
                continue
            seen.append(current)
            for need in self.needs.get(current, ()):
                if need not in self.licenses:
                    raise Missing(
                        f"{current} needs {need}, which carries "
                        "no license and cannot ship"
                    )
                frontier.append(need)
        return seen

    def _path_to(self, root: str, goal: str) -> list[str]:
        trail = {root: [root]}
        frontier = [root]
        while frontier:
            current = frontier.pop(0)
            if current == goal:
                return trail[current]
            for need in self.needs.get(current, ()):
                if need not in trail:
                    trail[need] = trail[current] + [need]
                    frontier.append(need)
        raise Missing(f"{goal} is not reachable from {root}")

    def check(
        self, target: str, allowed_kinds: tuple[str, ...]
    ) -> list[str]:
        for kind in allowed_kinds:
            if kind not in KINDS:
                raise Invalid(f"unknown license kind {kind}")
        violations = []
        for member in self.closure(target):
            kind = self.licenses[member].kind
            if kind not in allowed_kinds:
                path = " -> ".join(self._path_to(target, member))
                violations.append(
                    f"{path} ({self.licenses[member].name}, {kind})"
                )
        return violations

    def notice_file(self, target: str) -> str:
        obligations = {
            self.licenses[member].attribution
            for member in self.closure(target)
            if self.licenses[member].kind == NOTICE
        }
        if not obligations:
            return "no attribution obligations in the closure"
        return "\n".join(sorted(obligations))

    def verdict(
        self, target: str, allowed_kinds: tuple[str, ...]
    ) -> str:
        violations = self.check(target, allowed_kinds)
        if not violations:
            members = len(self.closure(target))
            return (
                f"{target} ships clean: {members} components, "
                f"policy {'/'.join(allowed_kinds)}"
            )
        lines = [
            f"{target} cannot ship under "
            f"{'/'.join(allowed_kinds)}: "
            f"{len(violations)} violation(s)"
        ]
        lines.extend(f"  {violation}" for violation in violations)
        return "\n".join(lines)
