"""Policy stacks: first match wins, and the shadowed rule never fires.

Access policies accrete like sediment: allow this team,
deny that path, allow the exception to the denial, each rule
written by someone solving that day's problem, evaluated top
down with the first match winning. The stack's characteristic
rot is the shadowed rule, one that can never fire because an
earlier, broader rule catches everything it would, and it is
worse than dead code because it looks like protection: the
auditor who reads "deny secrets/*" at position nine sleeps
well, not knowing position three allows the same path for
everyone. The linter finds shadows structurally, every rule
whose match set is swallowed by the union of earlier rules,
and reports each with its shadower, because the fix is a
reorder or a deletion and both need the pair named. Evaluation
itself logs which rule decided, since a policy that cannot say
why it answered is indistinguishable from a coin.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid


@dataclass(frozen=True)
class Rule:
    position: int
    effect: str
    pattern: str

    def __post_init__(self) -> None:
        if self.effect not in ("allow", "deny"):
            raise Invalid(
                f"rule {self.position}: effect must be allow "
                "or deny"
            )

    def matches(self, path: str) -> bool:
        if self.pattern.endswith("*"):
            return path.startswith(self.pattern[:-1])
        return path == self.pattern

    def swallows(self, other: Rule) -> bool:
        if self.pattern.endswith("*"):
            prefix = self.pattern[:-1]
            target = (
                other.pattern[:-1]
                if other.pattern.endswith("*")
                else other.pattern
            )
            return target.startswith(prefix)
        return self.pattern == other.pattern


@dataclass
class PolicyStack:
    rules: list[Rule]

    def evaluate(self, path: str) -> str:
        for rule in self.rules:
            if rule.matches(path):
                return (
                    f"{rule.effect} by rule {rule.position} "
                    f"({rule.pattern})"
                )
        return "deny by default; the stack ran out of opinions"

    def shadows(self) -> list[str]:
        found = []
        for index, rule in enumerate(self.rules):
            shadower = next(
                (
                    earlier
                    for earlier in self.rules[:index]
                    if earlier.swallows(rule)
                ),
                None,
            )
            if shadower is not None:
                found.append(
                    f"rule {rule.position} ({rule.effect} "
                    f"{rule.pattern}) can never fire: rule "
                    f"{shadower.position} ({shadower.effect} "
                    f"{shadower.pattern}) swallows it"
                )
        return found

    def lint(self) -> str:
        found = self.shadows()
        if not found:
            return (
                f"{len(self.rules)} rule(s), every one "
                "reachable"
            )
        lines = [
            f"{len(found)} shadowed rule(s); worse than dead "
            "code because they look like protection"
        ]
        lines.extend(f"  {entry}" for entry in found)
        return "\n".join(lines)
