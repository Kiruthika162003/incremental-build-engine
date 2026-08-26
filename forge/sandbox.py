"""The sandbox: an action sees its declared world and nothing else.

Observation catches leaks after the fact; the sandbox prevents them
by construction. The action runs against a view holding only its
declared reads, so an undeclared read is not a report line, it is a
Missing error at the exact moment of the crime with both names in
the message. Writes land in a staging area and are promoted to the
real tree only when the action finishes and wrote exactly what it
promised, which turns a half-failed action from a corrupted tree
into a no-op: the real world never sees partial output, and a rule
that dies after writing two of its three files leaves nothing
behind but the error. The cost is copying the declared inputs into
the view, and the meter prices that copy so the choice between
observe mode and sandbox mode is a receipt, not a religion.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.actions import Action
from forge.errors import Hermetic, Missing
from forge.workspace import Workspace


@dataclass
class SandboxRun:
    action: str
    promoted: list[str] = field(default_factory=list)
    bytes_copied_in: int = 0
    outcome: str = "pending"


class SandboxView:
    """The action's whole world: declared inputs plus a staging area."""

    def __init__(self, action: Action, tree: Workspace):
        self.action = action
        self.staging = Workspace()
        self.bytes_copied_in = 0
        for path in action.reads:
            payload = tree.read(path)
            self.staging.write(path, payload)
            self.bytes_copied_in += len(payload)

    def read(self, path: str) -> bytes:
        if path not in self.action.reads and not self.staging.exists(path):
            raise Hermetic(
                f"{self.action.name} read {path}, which it never "
                f"declared; the sandbox holds only "
                f"{sorted(self.action.reads)}"
            )
        return self.staging.read(path)

    def read_text(self, path: str) -> str:
        return self.read(path).decode("utf-8")

    def write(self, path: str, payload: bytes) -> str:
        return self.staging.write(path, payload)

    def write_text(self, path: str, text: str) -> str:
        return self.staging.write(path, text.encode("utf-8"))

    def exists(self, path: str) -> bool:
        return self.staging.exists(path)


def run_sandboxed(action: Action, tree: Workspace) -> SandboxRun:
    result = SandboxRun(action=action.name)
    view = SandboxView(action, tree)
    result.bytes_copied_in = view.bytes_copied_in
    try:
        action.rule(view)
    except (Hermetic, Missing):
        result.outcome = "refused"
        raise
    missing = [
        path for path in action.writes if not view.staging.exists(path)
    ]
    if missing:
        result.outcome = "refused"
        raise Hermetic(
            f"{action.name} promised {sorted(action.writes)} but "
            f"never wrote {missing}; nothing was promoted"
        )
    for path in action.writes:
        tree.write(path, view.staging.read(path))
        result.promoted.append(path)
    result.outcome = "promoted"
    return result


@dataclass
class SandboxMeter:
    runs: int = 0
    refusals: int = 0
    bytes_copied: int = 0

    def run(self, action: Action, tree: Workspace) -> SandboxRun:
        self.runs += 1
        try:
            result = run_sandboxed(action, tree)
        except Hermetic:
            self.refusals += 1
            raise
        self.bytes_copied += result.bytes_copied_in
        return result

    def receipt(self) -> str:
        return (
            f"{self.runs} sandboxed runs, {self.refusals} refused, "
            f"{self.bytes_copied} bytes copied in"
        )
