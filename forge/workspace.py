"""The workspace: an in-memory filesystem that tells the truth about reads.

The build system's view of the world is this tree of files, and the
tree keeps score: every read and write is counted per path, which is
what makes hermeticity checkable later, since an action that read a
file the workspace never saw it declare will be caught by arithmetic
rather than by luck. Writes bump a generation per path so tests can
assert not just what a build produced but whether it touched things
it had no business touching, and the tree digest gives any subtree
one identity, folding names and content the same way the content
module does, because a workspace and a cache that disagree about
what a tree is will disagree about everything downstream.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.content import digest_bytes, digest_pairs
from forge.errors import Invalid, Missing


@dataclass
class FileRecord:
    payload: bytes
    generation: int = 1
    reads: int = 0
    writes: int = 1


@dataclass
class Workspace:
    files: dict[str, FileRecord] = field(default_factory=dict)

    def write(self, path: str, payload: bytes) -> str:
        if not path or path.endswith("/"):
            raise Invalid(f"{path!r} is not a file path")
        record = self.files.get(path)
        if record is None:
            self.files[path] = FileRecord(payload=payload)
        else:
            record.payload = payload
            record.generation += 1
            record.writes += 1
        return digest_bytes(payload)

    def write_text(self, path: str, text: str) -> str:
        return self.write(path, text.encode("utf-8"))

    def read(self, path: str) -> bytes:
        record = self.files.get(path)
        if record is None:
            raise Missing(f"no file at {path}")
        record.reads += 1
        return record.payload

    def read_text(self, path: str) -> str:
        return self.read(path).decode("utf-8")

    def digest_of(self, path: str) -> str:
        """An identity peek that does not count as a read."""
        record = self.files.get(path)
        if record is None:
            raise Missing(f"no file at {path}")
        return digest_bytes(record.payload)

    def delete(self, path: str) -> None:
        if path not in self.files:
            raise Missing(f"no file at {path}")
        del self.files[path]

    def exists(self, path: str) -> bool:
        return path in self.files

    def under(self, prefix: str) -> list[str]:
        if prefix and not prefix.endswith("/"):
            prefix = prefix + "/"
        return sorted(
            path for path in self.files if path.startswith(prefix)
        )

    def tree_digest(self, prefix: str = "") -> str:
        rows = [
            (path, self.digest_of(path))
            for path in (self.under(prefix) if prefix else sorted(self.files))
        ]
        return digest_pairs(rows)

    def touch_counts(self, path: str) -> tuple[int, int]:
        record = self.files.get(path)
        if record is None:
            raise Missing(f"no file at {path}")
        return record.reads, record.writes

    def audit_line(self) -> str:
        reads = sum(record.reads for record in self.files.values())
        writes = sum(record.writes for record in self.files.values())
        return (
            f"{len(self.files)} files, {reads} reads, {writes} writes"
        )
