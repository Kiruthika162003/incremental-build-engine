"""The symbol server: strip the binary, keep the meaning, resolve the crash.

Shipping binaries carry no debug info and crashing binaries
demand it, so the debug halves live on a server keyed by
build id, the one string both halves share. Ingestion refuses a
debug blob without a build id outright, because an unkeyed
symbol file is write-only storage, and resolution walks a
crash's frames against the stored tables, naming function and
line for the frames it knows and being exact about the ones it
does not: a missing build id means the whole binary is a
stranger, usually a local build that never went through the
farm, while a known binary with an unknown address is
corruption or inlining and says which table it searched. The
retention tension is stated as policy: symbols outlive their
binaries, since the crash that arrives in month eleven does not
care that the artifact was garbage-collected in month two.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class SymbolServer:
    tables: dict[str, dict[int, str]] = field(
        default_factory=dict
    )
    ingested_order: list[str] = field(default_factory=list)

    def ingest(
        self, build_id: str, table: dict[int, str]
    ) -> str:
        if not build_id.strip():
            raise Invalid(
                "a debug blob without a build id is write-only "
                "storage; refuse it at the door"
            )
        if not table:
            raise Invalid(f"{build_id} carries an empty table")
        if build_id in self.tables:
            raise Invalid(
                f"{build_id} is already ingested; build ids do "
                "not get second opinions"
            )
        self.tables[build_id] = dict(table)
        self.ingested_order.append(build_id)
        return (
            f"{build_id}: {len(table)} symbol(s) stored; the "
            "binary may now be stripped"
        )

    def resolve_frame(self, build_id: str, address: int) -> str:
        table = self.tables.get(build_id)
        if table is None:
            return (
                f"0x{address:x} in {build_id}: the whole binary "
                "is a stranger; usually a local build that "
                "never went through the farm"
            )
        symbol = table.get(address)
        if symbol is None:
            return (
                f"0x{address:x} in {build_id}: known binary, "
                f"unknown address among {len(table)} symbol(s); "
                "corruption or inlining"
            )
        return f"0x{address:x} -> {symbol}"

    def resolve_crash(
        self, build_id: str, frames: list[int]
    ) -> str:
        if not frames:
            raise Invalid("a crash with no frames is a rumor")
        lines = [
            self.resolve_frame(build_id, address)
            for address in frames
        ]
        known = sum(1 for line in lines if " -> " in line)
        header = (
            f"{known} of {len(frames)} frame(s) resolved"
        )
        return "\n".join([header, *lines])

    def retention_note(self, binaries_alive: set[str]) -> str:
        orphaned = [
            build_id
            for build_id in self.ingested_order
            if build_id not in binaries_alive
        ]
        return (
            f"{len(orphaned)} symbol table(s) outlive their "
            "binaries, kept on purpose: the crash of month "
            "eleven does not care that the artifact was "
            "collected in month two"
        )
