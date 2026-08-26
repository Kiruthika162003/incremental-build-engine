"""Build health: five meters, one page, and a verdict that names its worst.

A build system degrades quietly along five independent axes, and
each has a meter elsewhere in this repository: cache hit rate,
hermeticity leaks, flaky rules, log determinism, and critical path
growth. The health page pulls one number from each and grades it
against a stated threshold, because a dashboard whose thresholds
live in someone's head is a mood ring. The composite verdict is
the minimum of the grades, never the average, since a build with a
97 percent hit rate and one hermeticity leak is a broken build
with a great cache, and averaging those two facts manufactures a
B-plus that nobody should believe. Each failing axis prints its
number, its threshold, and the module that owns the fix, so the
page ends where the work begins.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

AXES = (
    "cache_hit_rate",
    "hermetic_leaks",
    "flaky_rules",
    "log_deterministic",
    "path_growth_pct",
)

THRESHOLDS = {
    "cache_hit_rate": ("above", 0.5, "forge.cache"),
    "hermetic_leaks": ("at_most", 0, "forge.hermetic"),
    "flaky_rules": ("at_most", 0, "forge.flaky"),
    "log_deterministic": ("exactly", True, "forge.logmerge"),
    "path_growth_pct": ("at_most", 10, "forge.profile"),
}


@dataclass
class HealthReading:
    axis: str
    value: object

    def grade(self) -> bool:
        kind, bound, _ = THRESHOLDS[self.axis]
        if kind == "above":
            return self.value > bound
        if kind == "at_most":
            return self.value <= bound
        return self.value == bound

    def line(self) -> str:
        kind, bound, owner = THRESHOLDS[self.axis]
        state = "ok" if self.grade() else "FAILING"
        return (
            f"{self.axis}: {self.value} ({kind} {bound}) "
            f"[{state}, owner {owner}]"
        )


@dataclass
class HealthPage:
    readings: dict[str, HealthReading] = field(default_factory=dict)

    def take(self, axis: str, value: object) -> None:
        if axis not in AXES:
            raise Invalid(
                f"unknown axis {axis!r}; the page tracks {AXES}"
            )
        self.readings[axis] = HealthReading(axis=axis, value=value)

    def verdict(self) -> str:
        missing = [
            axis for axis in AXES if axis not in self.readings
        ]
        if missing:
            raise Invalid(
                f"the page is incomplete; no reading for {missing}"
            )
        failing = [
            reading
            for reading in self.readings.values()
            if not reading.grade()
        ]
        if not failing:
            return "healthy on all five axes"
        worst = failing[0]
        return (
            f"UNHEALTHY: {len(failing)} axis(es) failing, "
            f"start at {worst.axis} "
            f"(owner {THRESHOLDS[worst.axis][2]})"
        )

    def page(self) -> str:
        lines = [
            self.readings[axis].line()
            for axis in AXES
            if axis in self.readings
        ]
        lines.append(self.verdict())
        return "\n".join(lines)
