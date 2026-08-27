"""Incremental linking: patch the binary when you can, prove when you cannot.

A full link touches every object; an incremental link splices the
one changed object into the existing binary and is an order of
magnitude cheaper, but only inside its safety envelope. The
envelope is checkable: the changed object's symbol set must be
unchanged, its section sizes must fit the padding the last full
link reserved, and the binary being patched must descend from
this linker's own last output, verified by digest, because
patching a binary someone else produced is surgery on a stranger.
Any envelope violation falls back to a full link with the reason
recorded, never an error, since incremental linking is an
optimisation and an optimisation that can fail the build has been
promoted above its station. The ledger prices the season: patches
taken, full links forced, and ticks saved against the
always-full-link world.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.content import digest_text
from forge.errors import Invalid

FULL_LINK_COST = 40
PATCH_COST = 4


@dataclass
class ObjectState:
    symbols: tuple[str, ...]
    size: int


@dataclass
class IncrementalLinker:
    reserved_padding: int
    last_binary_digest: str | None = None
    last_objects: dict[str, ObjectState] = field(default_factory=dict)
    patches: int = 0
    full_links: int = 0
    fallback_reasons: list[str] = field(default_factory=list)

    def _full_link(
        self, objects: dict[str, ObjectState], reason: str | None
    ) -> str:
        self.full_links += 1
        if reason is not None:
            self.fallback_reasons.append(reason)
        self.last_objects = dict(objects)
        body = "|".join(
            f"{name}:{','.join(state.symbols)}:{state.size}"
            for name, state in sorted(objects.items())
        )
        self.last_binary_digest = digest_text(body)
        return f"full link ({reason or 'first build'})"

    def link(
        self,
        objects: dict[str, ObjectState],
        binary_digest: str | None,
    ) -> str:
        if not objects:
            raise Invalid("a link needs objects")
        if self.last_binary_digest is None:
            return self._full_link(objects, None)
        if binary_digest != self.last_binary_digest:
            return self._full_link(
                objects,
                "the binary on disk is not this linker's own child",
            )
        changed = [
            name
            for name, state in objects.items()
            if self.last_objects.get(name) != state
        ]
        arrivals = set(objects) - set(self.last_objects)
        departures = set(self.last_objects) - set(objects)
        if arrivals or departures:
            return self._full_link(
                objects,
                f"the object set changed "
                f"({sorted(arrivals | departures)})",
            )
        if len(changed) != 1:
            return self._full_link(
                objects,
                f"{len(changed)} objects changed; patching is a "
                f"one-object surgery",
            )
        name = changed[0]
        old = self.last_objects[name]
        new = objects[name]
        if old.symbols != new.symbols:
            return self._full_link(
                objects, f"{name}'s symbol set moved"
            )
        if new.size > old.size + self.reserved_padding:
            return self._full_link(
                objects,
                f"{name} outgrew its reserved padding",
            )
        self.patches += 1
        self.last_objects[name] = new
        return f"patched {name} in place"

    def season_ledger(self) -> str:
        always_full = (self.patches + self.full_links) * FULL_LINK_COST
        actual = (
            self.patches * PATCH_COST
            + self.full_links * FULL_LINK_COST
        )
        return (
            f"{self.patches} patches, {self.full_links} full links; "
            f"{always_full - actual} ticks saved against always-full"
        )
