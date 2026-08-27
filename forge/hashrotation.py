"""Rotating the digest algorithm: two hashes walk together until one retires.

The day the old hash is declared weak, the cache holds a
million entries keyed under it, and neither answer is
acceptable: trusting the weak hash forever, or evaporating the
farm's accumulated warmth overnight. The rotation walks the
middle: a dual-hash era in which every new entry is keyed under
both algorithms, every old entry gains its new key on first
verified read, re-hashed from the actual bytes rather than
translated, because a translation table from old key to new
key would inherit exactly the collisions the rotation exists
to escape. Cutover has a numeric gate, the share of live
entries carrying the new key, and after cutover old-only
entries are refused rather than migrated, since an entry
nobody read during the whole era is an entry whose bytes
nobody vouched for recently enough to bless with a new name.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

CUTOVER_SHARE = 0.9


@dataclass
class RotatingCache:
    entries: dict[str, dict[str, str]] = field(
        default_factory=dict
    )
    cut_over: bool = False

    def store(self, payload_id: str, old_key: str, new_key: str) -> None:
        if self.cut_over:
            self.entries[payload_id] = {"new": new_key}
            return
        self.entries[payload_id] = {
            "old": old_key,
            "new": new_key,
        }

    def adopt_legacy(self, payload_id: str, old_key: str) -> None:
        self.entries[payload_id] = {"old": old_key}

    def read(self, payload_id: str, rehash_new: str) -> str:
        held = self.entries.get(payload_id)
        if held is None:
            raise Invalid(f"{payload_id} is not in the cache")
        if "new" not in held:
            if self.cut_over:
                raise Invalid(
                    f"{payload_id} carries only the old key "
                    "after cutover: nobody vouched for its "
                    "bytes recently enough to bless it"
                )
            held["new"] = rehash_new
            return (
                f"{payload_id}: re-hashed from the bytes on "
                "first read; a translation table would inherit "
                "the collisions we are escaping"
            )
        return f"{payload_id}: served under the new key"

    def new_key_share(self) -> float:
        if not self.entries:
            raise Invalid("an empty cache has no share")
        carrying = sum(
            1
            for held in self.entries.values()
            if "new" in held
        )
        return carrying / len(self.entries)

    def attempt_cutover(self) -> str:
        share = self.new_key_share()
        if share < CUTOVER_SHARE:
            return (
                f"hold the era: {share:.0%} carry the new key "
                f"against a gate of {CUTOVER_SHARE:.0%}"
            )
        self.cut_over = True
        stragglers = sum(
            1
            for held in self.entries.values()
            if "new" not in held
        )
        return (
            f"cut over at {share:.0%}: {stragglers} old-only "
            "entrie(s) will be refused, not migrated"
        )
