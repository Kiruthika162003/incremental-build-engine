"""Derived paths: the output's address encodes what made it collide-free.

Two configurations building one target need two output paths, and
the naive scheme, appending the config name, collides the day
someone builds the same config with a different toolchain. The
layout derives each output's directory from a digest of the full
configuration, flags, platform, and toolchain together, so
distinct configurations cannot share a path by construction and
identical configurations always do, which is what lets a shared
output tree serve many configurations at once. The human half is
the legend: digests are opaque, so the layout keeps a legend
mapping each derived directory to the configuration that named
it, printable next to any path, because an output tree the team
cannot read is an output tree the team deletes and rebuilds from
scratch, which defeats every purpose the layout has.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.content import digest_text
from forge.errors import Invalid, Missing

LEGEND_WIDTH = 8


@dataclass(frozen=True)
class BuildConfig:
    platform: str
    flags: str
    toolchain: str

    def fingerprint(self) -> str:
        return digest_text(
            f"{self.platform}|{self.flags}|{self.toolchain}"
        )[:LEGEND_WIDTH]


@dataclass
class PathLayout:
    legend: dict[str, BuildConfig] = field(default_factory=dict)

    def derive(self, config: BuildConfig, target: str) -> str:
        if not target:
            raise Invalid("a target needs a name")
        prefix = config.fingerprint()
        held = self.legend.get(prefix)
        if held is not None and held != config:
            raise Invalid(
                f"fingerprint collision between {held} and {config}; "
                f"widen the legend"
            )
        self.legend[prefix] = config
        return f"out/{prefix}/{target}"

    def explain(self, path: str) -> str:
        parts = path.split("/")
        if len(parts) < 3 or parts[0] != "out":
            raise Invalid(f"{path} is not a derived output path")
        prefix = parts[1]
        config = self.legend.get(prefix)
        if config is None:
            raise Missing(
                f"no legend entry for {prefix}; this tree was built "
                f"by someone else's layout"
            )
        return (
            f"{path}: {config.platform}, {config.flags}, "
            f"{config.toolchain}"
        )

    def legend_page(self) -> str:
        if not self.legend:
            return "no derived paths yet"
        lines = [
            f"{prefix}: {config.platform} {config.flags} "
            f"{config.toolchain}"
            for prefix, config in sorted(self.legend.items())
        ]
        return "\n".join(lines)


def paths_disjoint(
    layout: PathLayout,
    first: BuildConfig,
    second: BuildConfig,
    target: str,
) -> bool:
    return layout.derive(first, target) != layout.derive(
        second, target
    )
