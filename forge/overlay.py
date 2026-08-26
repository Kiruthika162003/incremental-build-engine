"""The editor overlay: build what the buffer says, not what the disk holds.

An IDE asks for diagnostics against text the user has not saved,
and a build system that only reads disk answers questions about
the past. The overlay is a workspace view where unsaved buffers
shadow their files: reads and digests come from the buffer when
one exists and from the underlying tree otherwise, so action keys
move with the typing and the incremental machinery works unchanged
against a world that is partly imaginary. The discipline is in the
writes: build outputs land in the overlay only, never through to
the real tree, because a build against unsaved text producing real
artifacts is how a half-typed expression ends up linked into
something someone ships. Dropping a buffer un-shadows the file and
the next key computes from disk again, which is exactly what
closing an editor tab should mean.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.content import digest_bytes
from forge.errors import Missing
from forge.workspace import Workspace


@dataclass
class Overlay:
    base: Workspace
    buffers: dict[str, bytes] = field(default_factory=dict)
    outputs: dict[str, bytes] = field(default_factory=dict)
    reads_from_buffer: int = 0
    reads_from_disk: int = 0

    def open_buffer(self, path: str, text: str) -> None:
        self.buffers[path] = text.encode("utf-8")

    def drop_buffer(self, path: str) -> None:
        if path not in self.buffers:
            raise Missing(f"no open buffer for {path}")
        del self.buffers[path]

    def read(self, path: str) -> bytes:
        if path in self.outputs:
            return self.outputs[path]
        if path in self.buffers:
            self.reads_from_buffer += 1
            return self.buffers[path]
        self.reads_from_disk += 1
        return self.base.read(path)

    def read_text(self, path: str) -> str:
        return self.read(path).decode("utf-8")

    def write(self, path: str, payload: bytes) -> str:
        self.outputs[path] = payload
        return digest_bytes(payload)

    def write_text(self, path: str, text: str) -> str:
        return self.write(path, text.encode("utf-8"))

    def exists(self, path: str) -> bool:
        return (
            path in self.outputs
            or path in self.buffers
            or self.base.exists(path)
        )

    def digest_of(self, path: str) -> str:
        if path in self.outputs:
            return digest_bytes(self.outputs[path])
        if path in self.buffers:
            return digest_bytes(self.buffers[path])
        return self.base.digest_of(path)

    def files(self) -> dict:
        """Enough of the workspace surface for engine source checks."""
        return self.base.files

    def shadow_report(self) -> str:
        return (
            f"{len(self.buffers)} buffers shadowing, "
            f"{len(self.outputs)} imaginary outputs, "
            f"{self.reads_from_buffer} buffer reads, "
            f"{self.reads_from_disk} disk reads"
        )
