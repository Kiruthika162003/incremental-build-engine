"""Tree diffing: a move is a move, not a delete plus a stranger.

Diffing two output trees by path alone reports a renamed file
twice, once as a loss and once as an arrival, and a release page
built on that reads like a purge followed by a hiring spree.
Content addressing fixes the story: files pair by digest across
paths, so a payload that left one name and appeared under another
is reported as a move with both names, modified files pair by
path with differing digests, and only the truly new and truly
gone remain in those columns. The ambiguous case is handled by
refusing to guess: identical twins on both sides, two old paths
and two new paths sharing one digest, cannot be paired honestly
one-to-one, so they are reported as an unresolvable shuffle
rather than an invented pairing, because a diff that guesses is
a diff that lies confidently.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.content import digest_bytes


@dataclass
class TreeDelta:
    moved: list[tuple[str, str]] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    shuffled: list[str] = field(default_factory=list)

    def quiet(self) -> bool:
        return not (
            self.moved
            or self.modified
            or self.added
            or self.removed
            or self.shuffled
        )

    def page(self) -> str:
        if self.quiet():
            return "identical trees"
        lines = []
        for old, new in self.moved:
            lines.append(f"moved: {old} -> {new}")
        for path in self.modified:
            lines.append(f"modified: {path}")
        for path in self.added:
            lines.append(f"added: {path}")
        for path in self.removed:
            lines.append(f"removed: {path}")
        for digest in self.shuffled:
            lines.append(
                f"shuffle: several files share digest {digest}; "
                f"refusing to guess the pairing"
            )
        return "\n".join(lines)


def diff_trees(
    before: dict[str, bytes], after: dict[str, bytes]
) -> TreeDelta:
    delta = TreeDelta()
    before_digests = {
        path: digest_bytes(payload)
        for path, payload in before.items()
    }
    after_digests = {
        path: digest_bytes(payload)
        for path, payload in after.items()
    }
    for path in sorted(set(before) & set(after)):
        if before_digests[path] != after_digests[path]:
            delta.modified.append(path)
    gone = {
        path: before_digests[path]
        for path in before
        if path not in after
    }
    arrived = {
        path: after_digests[path]
        for path in after
        if path not in before
    }
    by_digest_gone: dict[str, list[str]] = {}
    for path, digest in gone.items():
        by_digest_gone.setdefault(digest, []).append(path)
    by_digest_arrived: dict[str, list[str]] = {}
    for path, digest in arrived.items():
        by_digest_arrived.setdefault(digest, []).append(path)
    for digest in sorted(
        set(by_digest_gone) | set(by_digest_arrived)
    ):
        old_paths = sorted(by_digest_gone.get(digest, []))
        new_paths = sorted(by_digest_arrived.get(digest, []))
        if len(old_paths) == 1 and len(new_paths) == 1:
            delta.moved.append((old_paths[0], new_paths[0]))
        elif old_paths and new_paths:
            delta.shuffled.append(digest)
        elif old_paths:
            delta.removed.extend(old_paths)
        else:
            delta.added.extend(new_paths)
    return delta
