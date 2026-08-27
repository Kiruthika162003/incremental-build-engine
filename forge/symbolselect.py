"""Interface digests: the file changed, but did the world's view of it change.

File-level cutoff already saves the day when an output comes back
byte-identical, but most edits are not byte-identical, they are
private: a body rewritten, a local helper renamed, a comment that
became code. The interface digest folds only what dependents can
see, the public symbol names and their signatures, so an edit
that leaves the interface digest alone can recompile one file and
stop, while dependents keep their objects. The split is the
measurement that matters: over an edit stream the selector counts
which saves came from file cutoff and which from interface
cutoff, because the second number is usually larger and is the
one a build team forgets to build. A public signature change
still ripples exactly as far as it must; the selector never
guesses, it compares digests.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.content import digest_pairs, digest_text
from forge.errors import Invalid, Missing


@dataclass(frozen=True)
class Symbol:
    name: str
    signature: str
    public: bool


@dataclass
class SourceUnit:
    path: str
    body: str
    symbols: tuple[Symbol, ...]

    def full_digest(self) -> str:
        return digest_text(self.body)

    def interface_digest(self) -> str:
        pairs = [
            (symbol.name, digest_text(symbol.signature))
            for symbol in sorted(
                self.symbols, key=lambda s: s.name
            )
            if symbol.public
        ]
        if not pairs:
            return digest_text("no public interface")
        return digest_pairs(pairs)


@dataclass
class InterfaceSelector:
    units: dict[str, SourceUnit] = field(default_factory=dict)
    dependents: dict[str, tuple[str, ...]] = field(
        default_factory=dict
    )
    file_saves: int = 0
    interface_saves: int = 0
    ripples: int = 0

    def admit(
        self, unit: SourceUnit, dependents: tuple[str, ...] = ()
    ) -> None:
        self.units[unit.path] = unit
        self.dependents[unit.path] = tuple(dependents)

    def edit(self, unit: SourceUnit) -> str:
        held = self.units.get(unit.path)
        if held is None:
            raise Missing(f"{unit.path} was never admitted")
        if unit.path != held.path:
            raise Invalid("an edit cannot rename the unit")
        watchers = self.dependents[unit.path]
        if unit.full_digest() == held.full_digest():
            self.file_saves += 1 + len(watchers)
            return (
                f"{unit.path} is byte-identical: nothing "
                "recompiles (file cutoff)"
            )
        same_interface = (
            unit.interface_digest() == held.interface_digest()
        )
        self.units[unit.path] = unit
        if same_interface:
            self.interface_saves += len(watchers)
            return (
                f"{unit.path} recompiles alone: the interface "
                f"digest held, {len(watchers)} dependent(s) keep "
                "their objects (interface cutoff)"
            )
        self.ripples += 1
        return (
            f"{unit.path} changed its public face: "
            f"{len(watchers)} dependent(s) recompile "
            f"({', '.join(watchers) if watchers else 'none'})"
        )

    def ledger(self) -> str:
        return (
            f"{self.file_saves} compiles saved by file cutoff, "
            f"{self.interface_saves} by interface cutoff, "
            f"{self.ripples} interface ripple(s) paid in full"
        )
