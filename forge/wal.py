"""The write-ahead journal: the build state survives the power cord.

Engine state updated in place is state that a crash can leave
half-written, and half-written state is worse than no state
because it replays as confidence. The journal is append-only:
every record carries its own digest, recovery reads forward
until the first record whose digest does not match its bytes,
truncates there, and reports how many records survived and what
was amputated, because a torn tail is expected physics, not an
error, and the only sin is replaying it. Replay is idempotent
by construction, records describe absolute states rather than
increments, so applying the journal twice lands on the same
state, which turns "did we already recover" from a dangerous
question into an uninteresting one. Compaction rewrites the
journal as one snapshot record when the tail grows long, and
the snapshot pays the same digest toll as any record, since a
corrupt snapshot with special privileges would be the single
point of failure the journal exists to remove.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.content import digest_text
from forge.errors import Invalid

COMPACT_THRESHOLD = 6


def _record(payload: str) -> str:
    return f"{digest_text(payload)[:12]}|{payload}"


def _validate(record: str) -> str | None:
    if "|" not in record:
        return None
    stamp, payload = record.split("|", 1)
    if digest_text(payload)[:12] != stamp:
        return None
    return payload


@dataclass
class Journal:
    records: list[str] = field(default_factory=list)

    def append(self, key: str, state: str) -> None:
        if "|" in key or "=" in key:
            raise Invalid(
                "keys carry no separators; the journal's format "
                "is not a suggestion"
            )
        self.records.append(_record(f"{key}={state}"))

    def simulate_torn_tail(self) -> None:
        if not self.records:
            raise Invalid("nothing to tear")
        self.records[-1] = self.records[-1][:-3] + "..."

    def recover(self) -> tuple[dict[str, str], str]:
        state: dict[str, str] = {}
        survived = 0
        for index, record in enumerate(self.records):
            payload = _validate(record)
            if payload is None:
                amputated = len(self.records) - index
                self.records = self.records[:index]
                return state, (
                    f"{survived} record(s) survived, "
                    f"{amputated} amputated at the torn tail; "
                    "expected physics, and the only sin is "
                    "replaying it"
                )
            key, value = payload.split("=", 1)
            if key == "snapshot":
                for pair in value.split(";"):
                    inner_key, inner_value = pair.split("=", 1)
                    state[inner_key] = inner_value
            else:
                state[key] = value
            survived += 1
        return state, f"{survived} record(s), no tear"

    def replay_twice_agrees(self) -> bool:
        first, _ = self.recover()
        second, _ = self.recover()
        return first == second

    def compact(self) -> str:
        state, verdict = self.recover()
        if "torn" in verdict:
            raise Invalid("recover before compacting a torn journal")
        if len(self.records) <= COMPACT_THRESHOLD:
            return (
                f"{len(self.records)} record(s) is under the "
                "threshold; compaction would churn for nothing"
            )
        snapshot = ";".join(
            f"{key}={value}" for key, value in sorted(state.items())
        )
        self.records = [_record(f"snapshot={snapshot}")]
        return (
            f"compacted to 1 snapshot record holding "
            f"{len(state)} key(s); it pays the same digest toll "
            "as any record"
        )
