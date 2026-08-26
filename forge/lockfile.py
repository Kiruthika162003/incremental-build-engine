"""The lockfile: resolve once, then let arithmetic guard the door.

External dependencies arrive with version ranges, and ranges are
promises about the future made by optimists. Resolution happens
once, deliberately: the resolver picks the newest version inside
each range, writes the pick and its content digest into the lock,
and every later install answers to the lock alone, never to the
range, so two machines a year apart install the same bytes. The
guard checks three betrayals by name: a package whose fetched
bytes stopped matching the locked digest, which is tampering or a
republished version and either way a stop; a lock entry no
manifest range covers anymore, which is a leftover; and a manifest
package with no lock entry, which is an unresolved newcomer. Range
drift is legal and invisible until re-resolution, because that is
the entire point of locking.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.content import digest_text
from forge.errors import Invalid, Missing


@dataclass(frozen=True)
class Available:
    name: str
    version: tuple[int, int]
    payload: str


@dataclass
class Registry:
    packages: dict[str, list[Available]] = field(default_factory=dict)

    def publish(self, release: Available) -> None:
        versions = self.packages.setdefault(release.name, [])
        if any(
            held.version == release.version for held in versions
        ):
            raise Invalid(
                f"{release.name} {release.version} is already "
                f"published; versions are immutable"
            )
        versions.append(release)

    def inside(
        self, name: str, floor: tuple[int, int], ceiling: tuple[int, int]
    ) -> list[Available]:
        return sorted(
            (
                release
                for release in self.packages.get(name, [])
                if floor <= release.version < ceiling
            ),
            key=lambda release: release.version,
        )


@dataclass
class LockEntry:
    name: str
    version: tuple[int, int]
    digest: str


def resolve(
    manifest: dict[str, tuple[tuple[int, int], tuple[int, int]]],
    registry: Registry,
) -> dict[str, LockEntry]:
    lock = {}
    for name, (floor, ceiling) in sorted(manifest.items()):
        candidates = registry.inside(name, floor, ceiling)
        if not candidates:
            raise Missing(
                f"nothing satisfies {name} in [{floor}, {ceiling})"
            )
        chosen = candidates[-1]
        lock[name] = LockEntry(
            name=name,
            version=chosen.version,
            digest=digest_text(chosen.payload),
        )
    return lock


def install(
    lock: dict[str, LockEntry], registry: Registry
) -> dict[str, str]:
    installed = {}
    for name, entry in sorted(lock.items()):
        release = next(
            (
                held
                for held in registry.packages.get(name, [])
                if held.version == entry.version
            ),
            None,
        )
        if release is None:
            raise Missing(
                f"{name} {entry.version} vanished from the registry"
            )
        if digest_text(release.payload) != entry.digest:
            raise Invalid(
                f"{name} {entry.version} does not match its locked "
                f"digest; tampering or a republish, either way a stop"
            )
        installed[name] = release.payload
    return installed


def audit_lock(
    manifest: dict[str, tuple[tuple[int, int], tuple[int, int]]],
    lock: dict[str, LockEntry],
) -> list[str]:
    complaints = []
    for name in sorted(manifest):
        if name not in lock:
            complaints.append(f"{name}: in the manifest, never resolved")
    for name, entry in sorted(lock.items()):
        window = manifest.get(name)
        if window is None:
            complaints.append(f"{name}: locked but no longer wanted")
            continue
        floor, ceiling = window
        if not floor <= entry.version < ceiling:
            complaints.append(
                f"{name}: locked at {entry.version}, outside "
                f"[{floor}, {ceiling})"
            )
    return complaints
