"""Provenance: the binary carries the story of everything that made it.

"What built this" is a question asked twice: by the security team
when a dependency turns out to be poisoned, and by the debugger
when production runs a binary nobody can reproduce. The manifest
answers both from the same record: every source digest, every
command, every intermediate, folded into one attestation digest
that names the whole story. Reproduction is the verb form of the
noun: replay the manifest against a fresh workspace and compare
the final digest, byte for byte, so "reproducible" is a check that
runs rather than a hope that persists. The poisoned-source query
walks the manifest backwards, answering which outputs a bad input
reached, and the answer is a list of names, since an incident
response that starts with a grep of build logs has already lost an
afternoon.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.content import digest_pairs, digest_text
from forge.engine import Engine
from forge.errors import Missing
from forge.workspace import Workspace


@dataclass
class ManifestEntry:
    target: str
    command: str
    input_digests: dict[str, str]
    output_digest: str


@dataclass
class Manifest:
    goal: str
    entries: dict[str, ManifestEntry] = field(default_factory=dict)
    source_digests: dict[str, str] = field(default_factory=dict)

    def attestation(self) -> str:
        rows = [
            (path, digest)
            for path, digest in self.source_digests.items()
        ]
        for name in sorted(self.entries):
            entry = self.entries[name]
            rows.append(
                (f"entry:{name}", digest_text(
                    f"{entry.command}|{entry.output_digest}"
                ))
            )
        return digest_pairs(rows)

    def reached_by(self, source: str) -> list[str]:
        if (
            source not in self.source_digests
            and source not in self.entries
        ):
            raise Missing(f"{source} is not in this build's story")
        poisoned = {source}
        changed = True
        while changed:
            changed = False
            for name, entry in self.entries.items():
                if name in poisoned:
                    continue
                if any(path in poisoned for path in entry.input_digests):
                    poisoned.add(name)
                    changed = True
        poisoned.discard(source)
        return sorted(poisoned)


def record(engine: Engine, goal: str, tree: Workspace) -> Manifest:
    engine.build(goal, tree)
    manifest = Manifest(goal=goal)
    for name in engine.graph.build_order(goal):
        action = engine.actions.get(name)
        if action is None:
            manifest.source_digests[name] = tree.digest_of(name)
            continue
        manifest.entries[name] = ManifestEntry(
            target=name,
            command=action.command,
            input_digests={
                path: tree.digest_of(path) for path in action.reads
            },
            output_digest=tree.digest_of(action.writes[0]),
        )
    return manifest


def reproduce(
    engine: Engine, manifest: Manifest, sources: dict[str, str]
) -> tuple[bool, str]:
    """Replay from sources alone and compare the attestations."""
    tree = Workspace()
    for path, text in sources.items():
        tree.write_text(path, text)
    fresh = record(engine, manifest.goal, tree)
    if fresh.attestation() == manifest.attestation():
        return True, "reproduced: the attestations match byte for byte"
    differing = sorted(
        name
        for name in manifest.entries
        if name in fresh.entries
        and fresh.entries[name].output_digest
        != manifest.entries[name].output_digest
    )
    return False, (
        f"NOT reproduced: outputs differ at {differing or 'the sources'}"
    )
