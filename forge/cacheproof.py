"""Cache correctness proofs: sample the hits and rebuild them anyway.

A cache with a subtle key bug does not fail; it succeeds with
the wrong bytes, quietly, for months, and the only defense is to
occasionally not believe it. The prover samples a deterministic
fraction of cache hits, rebuilds them from scratch on the side,
and compares digests: agreement is silent, disagreement is a
KEYBUG finding naming the action and both digests, which is the
loudest possible evidence that some input escaped the key. The
sampling rate is the knob between paranoia and thrift, and the
ledger prices it: verification ticks spent against hits sampled,
with the honest note that a season of silent agreement buys
confidence, not proof, because the prover only sees the keys
the sample happened to catch.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from forge.content import digest_text
from forge.errors import Invalid

Rebuilder = Callable[[str], str]


@dataclass
class CacheProver:
    sample_percent: int
    rebuild: Rebuilder
    sampled: int = 0
    agreed: int = 0
    verification_ticks: int = 0
    findings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0 < self.sample_percent <= 100:
            raise Invalid(
                "the sample rate must be between 1 and 100"
            )

    def _chosen(self, key: str) -> bool:
        bucket = int(digest_text(key)[:8], 16) % 100
        return bucket < self.sample_percent

    def audit_hit(
        self, key: str, cached_digest: str, rebuild_ticks: int
    ) -> str:
        if not self._chosen(key):
            return "trusted"
        self.sampled += 1
        self.verification_ticks += rebuild_ticks
        fresh = self.rebuild(key)
        if fresh == cached_digest:
            self.agreed += 1
            return "verified"
        finding = (
            f"KEYBUG {key}: cache served {cached_digest[:8]}, "
            f"a fresh build produced {fresh[:8]}; some input "
            "escaped the key"
        )
        self.findings.append(finding)
        return finding

    def ledger(self) -> str:
        if self.sampled == 0:
            return (
                "no hits sampled yet; confidence is exactly "
                "what it was this morning"
            )
        line = (
            f"{self.sampled} hit(s) sampled at "
            f"{self.sample_percent}%, {self.agreed} agreed, "
            f"{len(self.findings)} KEYBUG(s), "
            f"{self.verification_ticks} tick(s) spent"
        )
        if not self.findings:
            line += (
                "; a season of agreement buys confidence, "
                "not proof"
            )
        return line
