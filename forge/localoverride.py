"""Local overrides: point at your checkout, and wear the taint openly.

Debugging across two repositories means building against a local
checkout of the dependency instead of the locked release, and the
mechanism is fine while the honesty holds: the override book maps
a dependency to a local path, resolution prefers overrides while
they stand, and every artifact built under any override carries a
taint naming it, because the artifact embeds code that no lock,
registry, or reviewer ever saw. Tainted artifacts refuse release
outright, no flag to override the override, and the exit is as
explicit as the entrance: dropping the override lists the tainted
artifacts that must rebuild before the workspace tells the truth
again. The standing report shows every active override with its
age, since the two-day debugging aid that is still active in
month three is a fork wearing a bookmark's clothes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid, Missing


@dataclass
class OverrideBook:
    locked: dict[str, str]
    overrides: dict[str, tuple[str, int]] = field(
        default_factory=dict
    )
    tainted: dict[str, set[str]] = field(default_factory=dict)

    def override(
        self, dependency: str, local_path: str, now: int
    ) -> str:
        if dependency not in self.locked:
            raise Missing(
                f"{dependency} is not a locked dependency; there is "
                f"nothing to override"
            )
        if dependency in self.overrides:
            raise Invalid(f"{dependency} is already overridden")
        self.overrides[dependency] = (local_path, now)
        return (
            f"{dependency} now resolves to {local_path}; everything "
            f"built with it wears the taint"
        )

    def resolve(self, dependency: str) -> str:
        held = self.overrides.get(dependency)
        if held is not None:
            return held[0]
        version = self.locked.get(dependency)
        if version is None:
            raise Missing(f"{dependency} is not locked")
        return f"registry:{dependency}@{version}"

    def built(self, artifact: str, used: set[str]) -> str:
        active = sorted(set(self.overrides) & used)
        if active:
            self.tainted.setdefault(artifact, set()).update(active)
            return (
                f"{artifact} built TAINTED by {', '.join(active)}"
            )
        return f"{artifact} built clean"

    def may_release(self, artifact: str) -> str:
        stains = self.tainted.get(artifact)
        if stains:
            return (
                f"REFUSED: {artifact} embeds local checkouts of "
                f"{sorted(stains)} that no lock or reviewer ever saw"
            )
        return f"{artifact} may ship"

    def drop(self, dependency: str) -> str:
        if dependency not in self.overrides:
            raise Missing(f"{dependency} is not overridden")
        del self.overrides[dependency]
        must_rebuild = sorted(
            artifact
            for artifact, stains in self.tainted.items()
            if dependency in stains
        )
        for artifact in must_rebuild:
            self.tainted[artifact].discard(dependency)
            if not self.tainted[artifact]:
                del self.tainted[artifact]
        if must_rebuild:
            return (
                f"override dropped; rebuild "
                f"{', '.join(must_rebuild)} before the workspace "
                f"tells the truth again"
            )
        return "override dropped; nothing was built under it"

    def standing_report(self, now: int) -> str:
        if not self.overrides:
            return "no overrides; the lock speaks for everything"
        lines = []
        for dependency, (path, since) in sorted(
            self.overrides.items()
        ):
            age = now - since
            line = f"{dependency} -> {path} ({age} ticks standing)"
            if age > 100:
                line += "; a fork wearing a bookmark's clothes"
            lines.append(line)
        return "\n".join(lines)
