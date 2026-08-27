"""The nightly clean room: incremental state is trusted, then verified asleep.

Incremental builds accumulate state, and state accumulates
corruption vectors: a stale depfile, a mtime trick, a cache
entry from a buggy week. The clean room rebuilds everything from
nothing every night and compares digests key by key against the
day's incremental results, and the comparison has exactly three
outcomes: agreement, which renews trust for another day; an
incremental digest the clean build contradicts, which is
corruption with a name and the only correct response is
invalidating that entry and its cone; and keys only one side
built, which are drift in what the two worlds think the graph
is. The report ends with the trust verdict, because "the
incremental state was wrong about parser.o" on Tuesday is a
maintenance item, while three Tuesdays in a row is a bug in the
engine that the nightly just proved exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class CleanRoom:
    contradiction_history: list[int] = field(default_factory=list)

    def compare(
        self,
        incremental: dict[str, str],
        clean: dict[str, str],
    ) -> str:
        if not clean:
            raise Invalid(
                "the clean build produced nothing; that is an "
                "outage, not a comparison"
            )
        agreements = 0
        contradictions = []
        for key in sorted(set(incremental) & set(clean)):
            if incremental[key] == clean[key]:
                agreements += 1
            else:
                contradictions.append(
                    f"{key}: incremental {incremental[key][:8]} "
                    f"against clean {clean[key][:8]}; invalidate "
                    "the entry and its cone"
                )
        only_incremental = sorted(set(incremental) - set(clean))
        only_clean = sorted(set(clean) - set(incremental))
        self.contradiction_history.append(len(contradictions))
        lines = [
            f"{agreements} agreement(s), "
            f"{len(contradictions)} contradiction(s), "
            f"{len(only_incremental) + len(only_clean)} drift"
        ]
        lines.extend(f"  {entry}" for entry in contradictions)
        lines.extend(
            f"  drift: {key} exists only incrementally"
            for key in only_incremental
        )
        lines.extend(
            f"  drift: {key} exists only in the clean world"
            for key in only_clean
        )
        return "\n".join(lines)

    def trust_verdict(self) -> str:
        if not self.contradiction_history:
            raise Invalid("no nights compared yet")
        recent = self.contradiction_history[-3:]
        if all(count == 0 for count in recent):
            return (
                f"trust renewed: {len(self.contradiction_history)} "
                "night(s) compared, the recent ones clean"
            )
        dirty_nights = sum(1 for count in recent if count > 0)
        if dirty_nights >= 3:
            return (
                "ENGINE BUG: three consecutive nights of "
                "contradictions is not bad luck in the state, "
                "it is a defect in whatever maintains it"
            )
        return (
            f"maintenance: {dirty_nights} of the last "
            f"{len(recent)} night(s) had contradictions; "
            "invalidate and watch"
        )
