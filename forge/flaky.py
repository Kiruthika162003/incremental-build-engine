"""Flakiness detection: run it twice, and let the bytes testify.

A rule that embeds a timestamp, an absolute path, or an iteration
order produces different bytes from identical inputs, and every
such rule quietly destroys the cache above it: the same key maps
to two truths, early cutoff never fires, and the build farm pays
for determinism it is not getting. The detector runs each rule
twice against identical input trees and compares output digests;
byte-identical twice earns the rule a determinism certificate, a
mismatch names the differing paths. The double-run is expensive by
design and meant for CI, not for every build, which is why the
verdict is stored with the rule's key: a certificate survives
until the rule's command changes, and the certified list is the
set of rules the cache is allowed to believe.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.actions import Action, execute
from forge.errors import Invalid
from forge.workspace import Workspace


@dataclass(frozen=True)
class Verdict:
    action: str
    deterministic: bool
    differing: tuple[str, ...] = ()

    def line(self) -> str:
        if self.deterministic:
            return f"{self.action}: certified deterministic"
        return (
            f"{self.action}: FLAKY, outputs differ at "
            f"{list(self.differing)}"
        )


def _clone(tree: Workspace) -> Workspace:
    twin = Workspace()
    for path in sorted(tree.files):
        twin.write(path, tree.files[path].payload)
    return twin


def probe(action: Action, tree: Workspace) -> Verdict:
    first = _clone(tree)
    second = _clone(tree)
    execute(action, first)
    execute(action, second)
    differing = tuple(
        path
        for path in action.writes
        if first.digest_of(path) != second.digest_of(path)
    )
    return Verdict(
        action=action.name,
        deterministic=not differing,
        differing=differing,
    )


@dataclass
class Certifier:
    certificates: dict[str, Verdict] = field(default_factory=dict)
    probes_run: int = 0

    def _identity(self, action: Action) -> str:
        return f"{action.name}|{action.command}"

    def certify(self, action: Action, tree: Workspace) -> Verdict:
        identity = self._identity(action)
        held = self.certificates.get(identity)
        if held is not None:
            return held
        verdict = probe(action, tree)
        self.probes_run += 1
        self.certificates[identity] = verdict
        return verdict

    def believable(self, action: Action) -> bool:
        held = self.certificates.get(self._identity(action))
        return held is not None and held.deterministic

    def flaky_rules(self) -> list[str]:
        return sorted(
            verdict.action
            for verdict in self.certificates.values()
            if not verdict.deterministic
        )

    def revoke_on_command_change(self, action: Action) -> None:
        """A changed command invalidates its own certificate."""
        stale = [
            identity
            for identity in self.certificates
            if identity.startswith(f"{action.name}|")
            and identity != self._identity(action)
        ]
        for identity in stale:
            del self.certificates[identity]

    def registry_page(self) -> str:
        if not self.certificates:
            raise Invalid("nothing has been probed yet")
        lines = [
            self.certificates[identity].line()
            for identity in sorted(self.certificates)
        ]
        flaky = len(self.flaky_rules())
        lines.append(
            f"{len(self.certificates)} rules probed, {flaky} flaky"
        )
        return "\n".join(lines)
