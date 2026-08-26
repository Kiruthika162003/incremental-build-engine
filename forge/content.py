"""Content identity: a file is what it hashes to, not when it was saved.

Timestamp-based staleness lies in both directions: a touch without
a change rebuilds the world, and a change that lands inside the
clock's granularity rebuilds nothing. The digest is the identity,
computed over bytes and nothing else, and every other part of the
system speaks in digests so the question "did this change" always
means "did the bytes change". Directory digests fold their entries
in sorted order with names included, because two trees with the
same files under different names are different trees, and the fold
is stable across platforms since the sort is by name, not by the
filesystem's mood.
"""

from __future__ import annotations

import hashlib

from forge.errors import Invalid, Missing

DIGEST_BYTES = 16


def digest_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()[: DIGEST_BYTES * 2]


def digest_text(text: str) -> str:
    return digest_bytes(text.encode("utf-8"))


def digest_pairs(pairs: list[tuple[str, str]]) -> str:
    """A stable fold over (name, digest) rows, sorted by name."""
    if len({name for name, _ in pairs}) != len(pairs):
        raise Invalid("two entries share a name; the tree is ambiguous")
    folded = hashlib.sha256()
    for name, entry_digest in sorted(pairs):
        folded.update(name.encode("utf-8"))
        folded.update(b"\x00")
        folded.update(entry_digest.encode("ascii"))
        folded.update(b"\x01")
    return folded.hexdigest()[: DIGEST_BYTES * 2]


class ContentStore:
    """The CAS: bytes go in, a digest comes out, and that is the deal.

    Writing the same bytes twice costs one slot, which is the entire
    economy of a build cache: identical outputs from different
    actions, or the same action on different days, collapse into one
    stored object. The store never overwrites, because under content
    addressing an overwrite is either a no-op or a hash collision,
    and it refuses to pretend the second case is survivable.
    """

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.writes: int = 0
        self.deduplicated: int = 0

    def put(self, payload: bytes) -> str:
        key = digest_bytes(payload)
        if key in self.objects:
            if self.objects[key] != payload:
                raise Invalid(
                    "hash collision: two different payloads share a digest"
                )
            self.deduplicated += 1
            return key
        self.objects[key] = payload
        self.writes += 1
        return key

    def get(self, key: str) -> bytes:
        if key not in self.objects:
            raise Missing(f"no object with digest {key}")
        return self.objects[key]

    def has(self, key: str) -> bool:
        return key in self.objects

    def footprint(self) -> int:
        return sum(len(payload) for payload in self.objects.values())

    def economy(self) -> str:
        return (
            f"{self.writes} objects stored, {self.deduplicated} "
            f"duplicate puts collapsed, {self.footprint()} bytes held"
        )
