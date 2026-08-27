"""Deterministic archives: the same tree must make the same tarball.

Archive tools helpfully record timestamps, owners, and directory
order, and every one of those courtesies breaks reproducibility:
two builds of identical content produce different archives, the
cache misses, and the release manager diffs two multi-megabyte
blobs to learn that nothing changed. The deterministic writer
strips the courtesies by policy: entries sort by path, timestamps
are a fixed epoch, ownership is nobody, and the archive of a tree
is therefore a pure function of the tree's content. The
comparison method exists for the migration: given a sloppy
archive's entry list, it names each source of nondeterminism
found, because teams migrate archive by archive and the checklist
of what to fix is worth more than the lecture on why.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.content import digest_text
from forge.errors import Invalid

FIXED_EPOCH = 0
NOBODY = "0:0"


@dataclass(frozen=True)
class ArchiveEntry:
    path: str
    content_digest: str
    mtime: int
    owner: str


@dataclass
class Archive:
    entries: list[ArchiveEntry] = field(default_factory=list)

    def digest(self) -> str:
        folded = "|".join(
            f"{entry.path},{entry.content_digest},{entry.mtime},"
            f"{entry.owner}"
            for entry in self.entries
        )
        return digest_text(folded)


def write_deterministic(files: dict[str, str]) -> Archive:
    if not files:
        raise Invalid("an empty archive is a mistake upstream")
    entries = [
        ArchiveEntry(
            path=path,
            content_digest=digest_text(content),
            mtime=FIXED_EPOCH,
            owner=NOBODY,
        )
        for path, content in sorted(files.items())
    ]
    return Archive(entries=entries)


def write_sloppy(
    files: dict[str, str],
    clock: int,
    user: str,
    listing_order: list[str],
) -> Archive:
    """The tool being migrated away from, kept for the comparison."""
    entries = [
        ArchiveEntry(
            path=path,
            content_digest=digest_text(files[path]),
            mtime=clock,
            owner=user,
        )
        for path in listing_order
    ]
    return Archive(entries=entries)


def nondeterminism_sources(archive: Archive) -> list[str]:
    found = []
    paths = [entry.path for entry in archive.entries]
    if paths != sorted(paths):
        found.append(
            "entry order follows the directory listing, not the paths"
        )
    stamps = {entry.mtime for entry in archive.entries}
    if stamps != {FIXED_EPOCH}:
        found.append(
            f"timestamps recorded ({sorted(stamps)}); the clock is "
            f"in the archive"
        )
    owners = {entry.owner for entry in archive.entries}
    if owners != {NOBODY}:
        found.append(
            f"ownership recorded ({sorted(owners)}); the machine is "
            f"in the archive"
        )
    return found


def reproducibility_check(
    first: Archive, second: Archive
) -> str:
    if first.digest() == second.digest():
        return "reproducible: the archives are byte-identical"
    sources = set(nondeterminism_sources(first)) | set(
        nondeterminism_sources(second)
    )
    if sources:
        lines = ["NOT reproducible; the checklist:"]
        lines.extend(f"  {source}" for source in sorted(sources))
        return "\n".join(lines)
    return "NOT reproducible: the content itself differs"
