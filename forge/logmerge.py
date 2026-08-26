"""Merged build logs: concurrency may reorder work, never the story.

Eight workers interleave their output and the raw stream is
useless twice: lines from different actions shuffle together, and
two runs of the same build produce different logs, so diffing
yesterday's log against today's diffs the scheduler instead of the
build. The merger buffers per action and releases each action's
block only when it completes, ordered by the graph's deterministic
build order rather than by completion time, which makes the merged
log a pure function of the graph and the outputs: same build, same
log, byte for byte, whatever the workers did. Interleaving is
preserved inside an action because those lines belong together,
and the failure path prints the failing action's block last even
if it finished first, since the last thing a person reads should
be the reason they are reading.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class LogMerger:
    order: list[str]
    blocks: dict[str, list[str]] = field(default_factory=dict)
    completed: set[str] = field(default_factory=set)
    failed: str | None = None

    def __post_init__(self) -> None:
        if len(set(self.order)) != len(self.order):
            raise Invalid("the order lists a target twice")

    def emit(self, target: str, line: str) -> None:
        if target not in self.order:
            raise Invalid(f"{target} is not part of this build")
        if target in self.completed:
            raise Invalid(f"{target} already completed; too late to log")
        self.blocks.setdefault(target, []).append(line)

    def complete(self, target: str, failed: bool = False) -> None:
        if target in self.completed:
            raise Invalid(f"{target} completed twice")
        self.completed.add(target)
        if failed:
            if self.failed is not None:
                raise Invalid(
                    f"two failures ({self.failed}, {target}); a build "
                    f"stops at the first"
                )
            self.failed = target

    def merged(self) -> str:
        unfinished = [
            target
            for target in self.order
            if target in self.blocks and target not in self.completed
        ]
        if unfinished:
            raise Invalid(
                f"{unfinished[0]} logged but never completed; "
                f"the story is not over"
            )
        sections = []
        tail = None
        for target in self.order:
            if target not in self.blocks:
                continue
            block = [f"=== {target} ==="]
            block.extend(self.blocks[target])
            section = "\n".join(block)
            if target == self.failed:
                tail = section
            else:
                sections.append(section)
        if tail is not None:
            sections.append(tail)
        return "\n".join(sections)

    def is_deterministic_with(self, other: LogMerger) -> bool:
        return self.merged() == other.merged()
