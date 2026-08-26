"""The remote cache: a shared memory with a network bill attached.

A local cache remembers what this machine built; a remote cache
remembers what anyone built, which is why the first checkout of the
day can be ninety percent hits on a machine that has never compiled
a line. The economics are the design: every hit downloads bytes,
every miss uploads them, and the round trip is only worth paying
when the action's cost exceeds the transfer's. The policy knob is
therefore a threshold, not a boolean: cheap actions build locally
because shipping a two-tick string formatter across a network is
how build farms lose money, and the ledger prices both sides so
the threshold can be argued from the receipt instead of folklore.
Reads that race a concurrent upload are safe by construction, since
content addressing makes every stored value immutable: the worst
case is a duplicate upload, never a wrong download.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.actions import Action, execute
from forge.content import ContentStore
from forge.errors import Invalid
from forge.workspace import Workspace


@dataclass
class RemoteEntry:
    outputs: dict[str, str]
    cost: int


@dataclass
class RemoteStore:
    """The far side: entries plus the CAS, with transfer meters."""

    cas: ContentStore = field(default_factory=ContentStore)
    entries: dict[str, RemoteEntry] = field(default_factory=dict)
    bytes_downloaded: int = 0
    bytes_uploaded: int = 0
    round_trips: int = 0

    def lookup(self, key: str) -> RemoteEntry | None:
        self.round_trips += 1
        return self.entries.get(key)

    def download(self, digest: str) -> bytes:
        payload = self.cas.get(digest)
        self.bytes_downloaded += len(payload)
        return payload

    def upload(self, key: str, outputs: dict[str, bytes], cost: int) -> None:
        stored = {}
        for path, payload in outputs.items():
            self.bytes_uploaded += len(payload)
            stored[path] = self.cas.put(payload)
        self.entries[key] = RemoteEntry(outputs=stored, cost=cost)

    def traffic(self) -> str:
        return (
            f"{self.round_trips} round trips, "
            f"{self.bytes_downloaded} down, {self.bytes_uploaded} up"
        )


@dataclass
class RemoteBuilder:
    """A machine that consults the shared memory before working."""

    remote: RemoteStore
    upload_threshold: int = 3
    local_hits: int = 0
    remote_hits: int = 0
    built: int = 0
    kept_local: int = 0
    ticks_saved: int = 0
    local_entries: dict[str, RemoteEntry] = field(default_factory=dict)
    local_cas: ContentStore = field(default_factory=ContentStore)

    def run(self, action: Action, tree: Workspace, cost: int = 1) -> str:
        if cost < 0:
            raise Invalid("cost cannot be negative")
        key = action.key(tree)
        held = self.local_entries.get(key)
        if held is not None:
            for path, digest in held.outputs.items():
                tree.write(path, self.local_cas.get(digest))
            self.local_hits += 1
            self.ticks_saved += held.cost
            return "local-hit"
        if cost >= self.upload_threshold:
            found = self.remote.lookup(key)
            if found is not None:
                outputs = {}
                for path, digest in found.outputs.items():
                    payload = self.remote.download(digest)
                    tree.write(path, payload)
                    outputs[path] = self.local_cas.put(payload)
                self.local_entries[key] = RemoteEntry(
                    outputs=outputs, cost=found.cost
                )
                self.remote_hits += 1
                self.ticks_saved += found.cost
                return "remote-hit"
        execute(action, tree)
        self.built += 1
        payloads = {path: tree.read(path) for path in action.writes}
        self.local_entries[key] = RemoteEntry(
            outputs={
                path: self.local_cas.put(payload)
                for path, payload in payloads.items()
            },
            cost=cost,
        )
        if cost >= self.upload_threshold:
            self.remote.upload(key, payloads, cost)
        else:
            self.kept_local += 1
        return "built"

    def receipt(self) -> str:
        return (
            f"{self.local_hits} local hits, {self.remote_hits} remote "
            f"hits, {self.built} built ({self.kept_local} kept local), "
            f"{self.ticks_saved} ticks saved"
        )
