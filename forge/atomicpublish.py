"""Atomic output publication: the reader sees old bytes or new bytes, never both.

An action that writes its output in place invites every reader
that arrives mid-write to see a torn file, half old and half
new, valid to no parser and reproducible by no one. The
publisher writes to a temporary name in the same directory and
renames over the target as its last act, because rename within
a directory is the one atomic primitive the filesystem actually
grants, and everything else is hope. The simulator makes the
guarantee testable: a reader scheduled between any two steps of
a sloppy in-place write can observe a torn state, while the same
reader against the atomic publisher sees exactly the old digest
or the new one at every step, which is the whole contract. Crash
recovery is the quiet half: temporaries left by a crashed
publish are named by a sweep instead of shipped by accident,
since a stale temp that later gets renamed is yesterday's build
wearing today's name.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class PublishSim:
    files: dict[str, str] = field(default_factory=dict)
    log: list[str] = field(default_factory=list)

    def write_in_place(
        self, path: str, content: str
    ) -> list[str]:
        states = []
        old = self.files.get(path, "")
        for cut in range(1, len(content) + 1):
            torn = content[:cut] + old[cut:]
            self.files[path] = torn
            states.append(torn)
        self.files[path] = content
        self.log.append(f"in-place write of {path}")
        return states

    def publish_atomic(
        self, path: str, content: str
    ) -> list[str]:
        temp = f"{path}.tmp"
        states = []
        old = self.files.get(path)
        for cut in range(1, len(content) + 1):
            self.files[temp] = content[:cut]
            states.append(
                self.files.get(path) if old is not None else None
            )
        self.files[path] = self.files.pop(temp)
        self.log.append(f"atomic publish of {path}")
        return states

    def crash_during_publish(
        self, path: str, content: str
    ) -> None:
        self.files[f"{path}.tmp"] = content[: len(content) // 2]
        self.log.append(f"crash while publishing {path}")

    def sweep_temps(self) -> list[str]:
        stale = sorted(
            name for name in self.files if name.endswith(".tmp")
        )
        for name in stale:
            del self.files[name]
        return [
            f"{name}: removed; a stale temp renamed later is "
            "yesterday's build wearing today's name"
            for name in stale
        ]


def torn_states(
    old: str, observed_states: list[str]
) -> list[str]:
    return [
        state
        for state in observed_states
        if state not in (old, observed_states[-1])
    ]


def contract_verdict(
    old: str, new: str, observed_states: list[str | None]
) -> str:
    if not observed_states:
        raise Invalid("no observations to judge")
    seen = {
        state for state in observed_states if state is not None
    }
    illegal = seen - {old, new}
    if illegal:
        return (
            f"TORN: a reader observed {len(illegal)} state(s) "
            "that were neither the old bytes nor the new"
        )
    return (
        "atomic: every observation was the old bytes or the "
        "new bytes, never the truth in transit"
    )
