"""Fetch plans for the airgapped build: complete or failing at the worst time.

An offline build farm cannot discover a missing download at
minute forty of a release build; it has to know before the truck
leaves. The plan is computed from the pins: every external
component, its expected digest, and the mirror path derived from
both, name-digest prefixed so two versions of one package never
collide. Verifying a mirror against the plan yields three named
lists, missing, corrupt, and stray, because the three demand
different actions: missing means fetch again, corrupt means the
mirror or the pin is lying and someone must find out which, and
stray files are the mirror's rot, harmless today and confusing
forever. The verdict says ready only when missing and corrupt are
both empty; strays are reported but do not block, since blocking
a release on leftover files punishes the present for the past.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass(frozen=True)
class Pin:
    name: str
    version: str
    digest: str

    def __post_init__(self) -> None:
        if not self.digest or len(self.digest) < 8:
            raise Invalid(
                f"{self.name} pin needs a digest of at least 8 "
                "characters to be worth trusting"
            )

    def mirror_path(self) -> str:
        return (
            f"mirror/{self.name}/{self.digest[:8]}/"
            f"{self.name}-{self.version}.tar"
        )


@dataclass
class FetchPlan:
    pins: dict[str, Pin] = field(default_factory=dict)

    def add(self, pin: Pin) -> None:
        held = self.pins.get(pin.name)
        if held is not None and held.digest != pin.digest:
            raise Invalid(
                f"{pin.name} is pinned twice with different digests; "
                "one lockfile is lying"
            )
        self.pins[pin.name] = pin

    def manifest(self) -> list[str]:
        return [
            f"{pin.mirror_path()} sha256:{pin.digest}"
            for pin in sorted(
                self.pins.values(), key=lambda p: p.name
            )
        ]

    def verify(
        self, mirror: dict[str, str]
    ) -> tuple[list[str], list[str], list[str]]:
        missing = []
        corrupt = []
        expected_paths = set()
        for pin in sorted(self.pins.values(), key=lambda p: p.name):
            path = pin.mirror_path()
            expected_paths.add(path)
            held = mirror.get(path)
            if held is None:
                missing.append(path)
            elif held != pin.digest:
                corrupt.append(
                    f"{path} expected {pin.digest[:8]} "
                    f"found {held[:8]}"
                )
        stray = sorted(set(mirror) - expected_paths)
        return missing, corrupt, stray

    def verdict(self, mirror: dict[str, str]) -> str:
        missing, corrupt, stray = self.verify(mirror)
        if not missing and not corrupt:
            note = (
                f"; {len(stray)} stray file(s) rotting harmlessly"
                if stray
                else ""
            )
            return (
                f"the mirror is ready: {len(self.pins)} components "
                f"verified{note}"
            )
        lines = ["the truck cannot leave:"]
        lines.extend(f"  missing: {path}" for path in missing)
        lines.extend(f"  corrupt: {entry}" for entry in corrupt)
        return "\n".join(lines)
