"""The first build: the platform's first impression, measured in walls.

Nobody remembers their four hundredth build; everybody
remembers their first, and it is usually a tour of walls: the
tool the docs assumed, the environment variable one laptop in
the team exports, the cold cache that turns hello-world into
an hour. The scorecard clocks a new machine from clone to
first green and records every wall hit with its species,
because the fix for each species lives in a different place:
a missing tool belongs to the scaffold, an undocumented
variable belongs to the environment contract, and a cold
first hour belongs to the warming plan. The grade weights
walls over minutes, three fast walls read worse than one slow
clean run, since a wall teaches the new developer to ask a
human, and a platform whose onboarding requires asking a
human has a bus factor, not a first-build experience.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

WALL_SPECIES = {
    "missing-tool": "belongs to the scaffold",
    "undocumented-env": "belongs to the environment contract",
    "cold-cache": "belongs to the warming plan",
}


@dataclass
class FirstBuild:
    developer: str
    walls: list[tuple[str, str]] = field(default_factory=list)
    minutes_to_green: int | None = None

    def hit_wall(self, species: str, detail: str) -> str:
        if self.minutes_to_green is not None:
            raise Invalid(
                "walls after green are ordinary bugs; the "
                "first build is over"
            )
        owner = WALL_SPECIES.get(species)
        if owner is None:
            raise Invalid(
                f"unknown wall species {species}; new species "
                "are added deliberately, not improvised"
            )
        self.walls.append((species, detail))
        return f"{species}: {detail}; the fix {owner}"

    def reach_green(self, minutes: int) -> None:
        if minutes <= 0:
            raise Invalid("green takes time")
        self.minutes_to_green = minutes

    def scorecard(self) -> str:
        if self.minutes_to_green is None:
            raise Invalid(
                f"{self.developer} has not reached green; the "
                "scorecard waits"
            )
        wall_count = len(self.walls)
        if wall_count == 0:
            return (
                f"{self.developer}: green in "
                f"{self.minutes_to_green} minute(s), zero "
                "walls; the platform introduced itself"
            )
        lines = [
            f"{self.developer}: green in "
            f"{self.minutes_to_green} minute(s) through "
            f"{wall_count} wall(s), and walls outweigh minutes"
        ]
        for species, detail in self.walls:
            lines.append(
                f"  {species}: {detail}; the fix "
                f"{WALL_SPECIES[species]}"
            )
        lines.append(
            "every wall teaches the new developer to ask a "
            "human, and that is a bus factor, not an "
            "onboarding"
        )
        return "\n".join(lines)
