"""Result validation: the rule exited zero, which proves nothing.

Compilers have written empty object files with a success exit
since before anyone reading this was born, and the cache is the
worst place to discover it: an empty artifact cached once is
served forever, correct by key and worthless by content. The
validator runs declared checks per output before the cache is
allowed to remember anything: nonempty is the floor, magic bytes
catch the truncated write, and the custom predicate carries
whatever the format knows about itself. A failed check quarantines
the result exactly like a hermeticity leak, executed but never
cached, with the check's name in the refusal, and the ledger
counts saves, results that exited zero and were still refused,
because that number is the validator's entire salary and it is
usually not zero.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from forge.errors import Invalid
from forge.workspace import Workspace

Check = Callable[[bytes], str | None]


def nonempty(payload: bytes) -> str | None:
    if not payload:
        return "the output is empty"
    return None


def magic(expected: bytes) -> Check:
    def check(payload: bytes) -> str | None:
        if not payload.startswith(expected):
            return (
                f"missing magic bytes {expected!r}; the write was "
                f"truncated or the tool wrote garbage"
            )
        return None

    return check


@dataclass
class Validator:
    checks: dict[str, list[Check]] = field(default_factory=dict)
    saves: list[str] = field(default_factory=list)
    passed: int = 0

    def require(self, path: str, check: Check) -> None:
        self.checks.setdefault(path, []).append(check)

    def validate(self, path: str, tree: Workspace) -> None:
        payload = tree.read(path)
        for check in [nonempty, *self.checks.get(path, [])]:
            complaint = check(payload)
            if complaint is not None:
                self.saves.append(f"{path}: {complaint}")
                raise Invalid(
                    f"{path} failed validation ({complaint}); "
                    f"executed but never cached"
                )
        self.passed += 1

    def validate_all(
        self, paths: tuple[str, ...], tree: Workspace
    ) -> None:
        for path in paths:
            self.validate(path, tree)

    def salary(self) -> str:
        return (
            f"{len(self.saves)} results exited zero and were still "
            f"refused; {self.passed} passed"
        )
