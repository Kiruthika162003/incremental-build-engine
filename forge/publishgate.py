"""The publish gate: a version leaves when every clerk has signed.

Publishing a package version is five small promises made at
once: the number matches the interface diff, the changelog has
an entry for it, the attribution file covers the closure, no
local patch is still riding on vendored code, and the docs
samples still compile. Each clerk checks one promise and the
gate publishes only on five signatures, reporting every refusal
at once rather than one per attempt, because a release manager
who fixes the changelog and then discovers the version number
is also wrong learns to distrust the gate one round trip at a
time. The signatures are recorded with the release, so the
question "was 3.1.0 checked" has an answer better than
"probably", and a gate bypassed in an emergency leaves a
bypass record, since the honest history of exceptions is what
keeps the rule alive.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid
from forge.semver import advise


@dataclass
class PublishGate:
    published: dict[str, tuple[str, ...]] = field(
        default_factory=dict
    )
    bypasses: list[str] = field(default_factory=list)

    def check(
        self,
        version: str,
        proposed_bump: str,
        before_face: dict[str, str],
        after_face: dict[str, str],
        changelog_versions: tuple[str, ...],
        notice_current: bool,
        stale_patches: tuple[str, ...],
        rotted_samples: int,
    ) -> list[str]:
        refusals = []
        advice = advise(before_face, after_face)
        if proposed_bump != advice.bump:
            refusals.append(
                f"version clerk: the diff demands {advice.bump} "
                f"({', '.join(advice.reasons) or 'no reasons'}), "
                f"the proposal says {proposed_bump}"
            )
        if version not in changelog_versions:
            refusals.append(
                f"changelog clerk: no entry for {version}"
            )
        if not notice_current:
            refusals.append(
                "attribution clerk: the NOTICE file lags the "
                "closure"
            )
        if stale_patches:
            refusals.append(
                f"vendor clerk: {', '.join(stale_patches)} "
                "still ride the old base"
            )
        if rotted_samples:
            refusals.append(
                f"docs clerk: {rotted_samples} sample(s) no "
                "longer compile"
            )
        return refusals

    def publish(self, version: str, **facts) -> str:
        if version in self.published:
            raise Invalid(f"{version} is already published")
        refusals = self.check(version, **facts)
        if refusals:
            raise Invalid(
                f"{version} refused by {len(refusals)} "
                "clerk(s), all reported at once:\n"
                + "\n".join(f"  {line}" for line in refusals)
            )
        signatures = (
            "version",
            "changelog",
            "attribution",
            "vendor",
            "docs",
        )
        self.published[version] = signatures
        return (
            f"{version} published with {len(signatures)} "
            "signature(s) on record"
        )

    def bypass(self, version: str, reason: str) -> str:
        if not reason.strip():
            raise Invalid(
                "an emergency without a written reason is just "
                "a habit starting"
            )
        self.published[version] = ("BYPASSED",)
        self.bypasses.append(f"{version}: {reason}")
        return (
            f"{version} published on a bypass; the honest "
            "history of exceptions is what keeps the rule alive"
        )

    def audit_trail(self, version: str) -> str:
        held = self.published.get(version)
        if held is None:
            raise Invalid(f"{version} was never published")
        if held == ("BYPASSED",):
            note = next(
                entry
                for entry in self.bypasses
                if entry.startswith(version)
            )
            return f"{version}: BYPASSED ({note.split(': ', 1)[1]})"
        return f"{version}: signed by {', '.join(held)}"
