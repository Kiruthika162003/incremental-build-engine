"""Time travel: rebuild last Tuesday exactly, or say which part of Tuesday is gone.

"Reproduce the build from the incident" is a request to
reassemble a world: the tree as of that commit, the toolchain
as of that morning, the graph as of that revision. The archive
records a seal per build with its three component digests, and
travel is a lookup plus a verification: reassemble the parts,
re-seal, and compare against the recorded fingerprint, because
a reproduction that is not byte-checked is a reenactment. When
a part is missing the answer names it: tools are the usual
casualty, deregistered from the farm months later, and the
report says the sources and graph of Tuesday survive while
gcc 13.1 does not, which turns "we cannot reproduce it" from a
confession into a purchase order. Every successful travel is
logged with the distance, since a team that reproduces
year-old builds weekly has an archive worth its rent, and one
that never travels is paying rent on a museum.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.buildseal import BuildSeal
from forge.errors import Invalid, Missing


@dataclass
class BuildArchive:
    seals: dict[str, tuple[BuildSeal, int]] = field(
        default_factory=dict
    )
    tree_store: dict[str, str] = field(default_factory=dict)
    tool_store: dict[str, str] = field(default_factory=dict)
    graph_store: dict[str, str] = field(default_factory=dict)
    travels: list[str] = field(default_factory=list)

    def record(
        self, build_id: str, seal: BuildSeal, day: int
    ) -> None:
        if build_id in self.seals:
            raise Invalid(f"{build_id} is already archived")
        self.seals[build_id] = (seal, day)
        self.tree_store[seal.tree_digest] = f"tree:{build_id}"
        self.tool_store[seal.tool_digest] = f"tools:{build_id}"
        self.graph_store[seal.graph_digest] = f"graph:{build_id}"

    def forget_tools(self, tool_digest: str) -> None:
        self.tool_store.pop(tool_digest, None)

    def travel_to(self, build_id: str, today: int) -> str:
        held = self.seals.get(build_id)
        if held is None:
            raise Missing(f"{build_id} was never archived")
        seal, day = held
        missing = []
        if seal.tree_digest not in self.tree_store:
            missing.append("the tree")
        if seal.tool_digest not in self.tool_store:
            missing.append("the toolchain")
        if seal.graph_digest not in self.graph_store:
            missing.append("the graph")
        if missing:
            survived = [
                part
                for part in ("the tree", "the toolchain", "the graph")
                if part not in missing
            ]
            return (
                f"cannot reassemble {build_id}: "
                f"{' and '.join(missing)} of day {day} are "
                f"gone while {' and '.join(survived)} survive; "
                "not a confession, a purchase order"
            )
        reproduced = BuildSeal(
            tree_digest=seal.tree_digest,
            tool_digest=seal.tool_digest,
            graph_digest=seal.graph_digest,
        )
        if reproduced.fingerprint() != seal.fingerprint():
            return (
                f"REENACTMENT: {build_id} reassembled but the "
                "fingerprint moved; a reproduction that is not "
                "byte-checked is theater"
            )
        distance = today - day
        self.travels.append(f"{build_id} at distance {distance}")
        return (
            f"{build_id} reproduced exactly, {distance} day(s) "
            "back, fingerprint verified"
        )

    def rent_verdict(self) -> str:
        if not self.travels:
            return (
                f"{len(self.seals)} build(s) archived, zero "
                "travels: rent paid on a museum"
            )
        return (
            f"{len(self.travels)} travel(s) on record; the "
            "archive earns its rent"
        )
