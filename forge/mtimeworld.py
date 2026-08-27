"""The timestamp world, simulated: every lie it tells, counted.

The oldest staleness model rebuilds when an input's clock is newer
than the output's, and its two lies are structural. The touch lie:
saving a file without changing it bumps the clock and rebuilds the
cone for nothing, and checkout tools touch everything. The clock
lie: a change landing inside the same tick as the previous build
leaves the timestamps equal and the target quietly stale, which is
the bug that ships. This module runs both models over one scripted
day and counts the disagreements: false rebuilds where mtime paid
and content did not, and stale serves where mtime skipped work
that content knew was needed. The second column matters more at
any count, and the day's receipt says so in its shape: waste is a
number, staleness is a list of names, because wasted rebuilds cost
minutes and stale artifacts cost belief.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.content import digest_bytes
from forge.errors import Invalid


@dataclass
class TimestampedFile:
    payload: bytes
    mtime: int


@dataclass
class TwoWorldTracker:
    files: dict[str, TimestampedFile] = field(default_factory=dict)
    built_mtime: dict[str, int] = field(default_factory=dict)
    built_digest: dict[str, str] = field(default_factory=dict)
    false_rebuilds: int = 0
    stale_serves: list[str] = field(default_factory=list)

    def save(self, path: str, payload: bytes, clock: int) -> None:
        self.files[path] = TimestampedFile(payload=payload, mtime=clock)

    def touch(self, path: str, clock: int) -> None:
        if path not in self.files:
            raise Invalid(f"cannot touch {path}; it does not exist")
        self.files[path].mtime = clock

    def build(self, target: str, source: str, clock: int) -> dict:
        held = self.files.get(source)
        if held is None:
            raise Invalid(f"{source} does not exist")
        mtime_says_rebuild = (
            target not in self.built_mtime
            or held.mtime > self.built_mtime[target]
        )
        fresh_digest = digest_bytes(held.payload)
        content_says_rebuild = (
            self.built_digest.get(target) != fresh_digest
        )
        if mtime_says_rebuild and not content_says_rebuild:
            self.false_rebuilds += 1
        if content_says_rebuild and not mtime_says_rebuild:
            self.stale_serves.append(target)
        if mtime_says_rebuild:
            self.built_mtime[target] = clock
        if content_says_rebuild:
            self.built_digest[target] = fresh_digest
        return {
            "mtime": "rebuild" if mtime_says_rebuild else "skip",
            "content": "rebuild" if content_says_rebuild else "skip",
        }

    def receipt(self) -> str:
        if not self.stale_serves:
            return (
                f"{self.false_rebuilds} false rebuilds, no stale "
                f"serves; the clock only wasted time today"
            )
        return (
            f"{self.false_rebuilds} false rebuilds, and the clock "
            f"shipped stale: {sorted(set(self.stale_serves))}"
        )
