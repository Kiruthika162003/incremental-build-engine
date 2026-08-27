"""The execution log: what actually ran, replayable and comparable.

When two machines disagree about a build, the argument is settled
by their execution logs: every spawn recorded with its key, its
inputs' digests, its outcome, and its duration, in execution
order. The comparator aligns two logs by action key and reports
the first divergence with everything needed to reproduce it,
which inputs differed, whose command drifted, or whether one
machine simply never ran the action, because the first divergence
is the cause and everything after it is weather. Replay mode
re-executes a log's actions against a fresh workspace and checks
each output digest as it goes, stopping at the first mismatch
with the log's line number, turning "it worked on the CI machine"
from a shrug into a coordinate.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.actions import Action, execute
from forge.errors import Invalid
from forge.workspace import Workspace


@dataclass(frozen=True)
class LogLine:
    key: str
    action: str
    input_digests: tuple[tuple[str, str], ...]
    output_digest: str
    duration: int


@dataclass
class ExecutionLog:
    lines: list[LogLine] = field(default_factory=list)

    def record(
        self, action: Action, tree: Workspace, duration: int
    ) -> None:
        self.lines.append(
            LogLine(
                key=action.key(tree),
                action=action.name,
                input_digests=tuple(
                    (path, tree.digest_of(path))
                    for path in action.reads
                ),
                output_digest=tree.digest_of(action.writes[0]),
                duration=duration,
            )
        )


def first_divergence(
    ours: ExecutionLog, theirs: ExecutionLog
) -> str | None:
    theirs_by_action = {
        line.action: line for line in theirs.lines
    }
    for line in ours.lines:
        other = theirs_by_action.get(line.action)
        if other is None:
            return (
                f"{line.action}: we ran it, they never did; "
                f"everything after this is weather"
            )
        if line.key != other.key:
            our_inputs = dict(line.input_digests)
            their_inputs = dict(other.input_digests)
            differing = sorted(
                path
                for path in set(our_inputs) | set(their_inputs)
                if our_inputs.get(path) != their_inputs.get(path)
            )
            if differing:
                return (
                    f"{line.action}: inputs differ at {differing}"
                )
            return (
                f"{line.action}: same inputs, different key; a "
                f"command drifted"
            )
        if line.output_digest != other.output_digest:
            return (
                f"{line.action}: same key, different output; one "
                f"side is not deterministic"
            )
    return None


def replay(
    log: ExecutionLog,
    actions: dict[str, Action],
    tree: Workspace,
) -> str:
    for number, line in enumerate(log.lines, start=1):
        action = actions.get(line.action)
        if action is None:
            raise Invalid(
                f"log line {number}: no action named {line.action}"
            )
        execute(action, tree)
        fresh = tree.digest_of(action.writes[0])
        if fresh != line.output_digest:
            return (
                f"MISMATCH at log line {number}: {line.action} "
                f"produced {fresh}, the log says "
                f"{line.output_digest}"
            )
    return f"replayed {len(log.lines)} lines byte for byte"
