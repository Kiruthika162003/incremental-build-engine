"""Lazy materialisation: download the binary, leave the objects in the sky.

A remote build produces hundreds of intermediates the developer
will never open, and downloading them all turns a fast remote
build into a slow local sync. The lazy tree keeps every output as
a digest reference; bytes come down only when something actually
asks, the developer opening the final binary or a local action
consuming an intermediate as input. The ledger splits the traffic
into materialised on demand and never fetched, and the ratio is
the feature's entire justification: a build whose intermediates
are 90 percent of the bytes and 0 percent of the opens pays for
this module in one afternoon. The trap is a reference outliving
its CAS entry, so materialisation of an evicted digest fails with
the eviction's own postmortem rather than a bare not-found,
because the user's question is never "what is missing", it is
"who decided to forget it".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.content import ContentStore
from forge.errors import Missing, Stale


@dataclass
class LazyReference:
    path: str
    digest: str
    size: int


@dataclass
class LazyTree:
    store: ContentStore
    references: dict[str, LazyReference] = field(default_factory=dict)
    materialised: dict[str, bytes] = field(default_factory=dict)
    bytes_fetched: int = 0
    evicted_reasons: dict[str, str] = field(default_factory=dict)

    def refer(self, path: str, payload: bytes) -> None:
        digest = self.store.put(payload)
        self.references[path] = LazyReference(
            path=path, digest=digest, size=len(payload)
        )

    def evict(self, path: str, reason: str) -> None:
        held = self.references.get(path)
        if held is None:
            raise Missing(f"no reference at {path}")
        if held.digest in self.store.objects:
            del self.store.objects[held.digest]
        self.evicted_reasons[held.digest] = reason

    def open(self, path: str) -> bytes:
        if path in self.materialised:
            return self.materialised[path]
        held = self.references.get(path)
        if held is None:
            raise Missing(f"no output at {path}")
        if not self.store.has(held.digest):
            reason = self.evicted_reasons.get(
                held.digest, "unknown eviction"
            )
            raise Stale(
                f"{path} was forgotten before it was opened: {reason}"
            )
        payload = self.store.get(held.digest)
        self.materialised[path] = payload
        self.bytes_fetched += held.size
        return payload

    def ledger(self) -> str:
        total = sum(
            reference.size for reference in self.references.values()
        )
        never = total - self.bytes_fetched
        share = never / total if total else 0.0
        return (
            f"{self.bytes_fetched} bytes materialised, {never} never "
            f"fetched ({share:.0%} of the build stayed in the sky)"
        )
