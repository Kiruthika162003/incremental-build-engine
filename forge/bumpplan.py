"""Dependency bump planning: one lockstep bump is a bisection you cannot run.

The Friday habit of bumping fourteen dependencies in one commit
works until the first regression, at which point the team owns a
haystack with fourteen needles and a bisect that lands on the
whole commit. The planner orders pending bumps so each lands
alone and bisectable, riskiest last, where risk is what can be
computed without opinions: the fan-in of the dependency in the
local graph times the size of the version jump. Bumps that share
a constraint edge, one package requiring a floor of another, are
fused into the smallest group that can land together, and the
plan says why each fusion happened, because a grouped bump is a
concession, not a convenience, and the plan should read like it
knows the difference.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

JUMP_WEIGHT = {"patch": 1, "minor": 3, "major": 9}


@dataclass(frozen=True)
class Bump:
    package: str
    jump: str
    fan_in: int

    def __post_init__(self) -> None:
        if self.jump not in JUMP_WEIGHT:
            raise Invalid(
                f"{self.package} jump must be one of "
                f"{tuple(JUMP_WEIGHT)}"
            )
        if self.fan_in < 0:
            raise Invalid("fan-in cannot be negative")

    def risk(self) -> int:
        return JUMP_WEIGHT[self.jump] * max(1, self.fan_in)


@dataclass
class BumpPlanner:
    bumps: dict[str, Bump] = field(default_factory=dict)
    ties: list[tuple[str, str, str]] = field(default_factory=list)

    def add(self, bump: Bump) -> None:
        if bump.package in self.bumps:
            raise Invalid(f"{bump.package} is already planned")
        self.bumps[bump.package] = bump

    def tie(self, first: str, second: str, reason: str) -> None:
        for package in (first, second):
            if package not in self.bumps:
                raise Invalid(
                    f"{package} is not in the plan; a tie needs "
                    "both ends"
                )
        self.ties.append((first, second, reason))

    def _groups(self) -> list[tuple[list[str], list[str]]]:
        parent = {name: name for name in self.bumps}

        def find(name: str) -> str:
            while parent[name] != name:
                parent[name] = parent[parent[name]]
                name = parent[name]
            return name

        reasons: dict[str, list[str]] = {}
        for first, second, reason in self.ties:
            root_a, root_b = find(first), find(second)
            if root_a != root_b:
                parent[root_b] = root_a
            reasons.setdefault(find(first), []).append(reason)
        collected: dict[str, list[str]] = {}
        for name in self.bumps:
            collected.setdefault(find(name), []).append(name)
        return [
            (sorted(members), reasons.get(root, []))
            for root, members in collected.items()
        ]

    def plan(self) -> str:
        if not self.bumps:
            raise Invalid("nothing to bump")
        groups = self._groups()
        ordered = sorted(
            groups,
            key=lambda g: (
                sum(self.bumps[m].risk() for m in g[0]),
                g[0][0],
            ),
        )
        lines = [
            f"{len(self.bumps)} bump(s) in {len(ordered)} "
            "landing(s), riskiest last"
        ]
        for position, (members, reasons) in enumerate(ordered, 1):
            total = sum(self.bumps[m].risk() for m in members)
            label = " + ".join(members)
            lines.append(
                f"  {position}. {label} (risk {total})"
            )
            for reason in reasons:
                lines.append(f"     fused: {reason}")
        return "\n".join(lines)

    def haystack_price(self) -> str:
        landings = len(self._groups())
        one_shot_suspects = len(self.bumps)
        return (
            f"a regression after the plan suspects at most the "
            f"latest landing; after the Friday lockstep it "
            f"suspects all {one_shot_suspects}, and the bisect "
            f"lands on the whole commit ({landings} landings "
            "buy that difference)"
        )
