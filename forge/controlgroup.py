"""The cache control group: one build in a hundred runs cold on purpose.

Every cache dashboard reports the benefit of the cache using
numbers the cache itself produced, which is a witness testifying
at its own trial. The control group fixes the epistemology: a
deterministic slice of builds runs with the cache disabled, and
the claimed speedup becomes a measured ratio between the control
group's wall clock and everyone else's. The control also catches
what no hit-rate graph can: if cached builds and cold builds
disagree on output digests, the cache is fast and wrong, which
the comparison names with the key, and fast-and-wrong is the
only cache property that matters more than speed. The cost of
the program is stated plainly, control builds pay full price by
design, and the report divides that cost by what the measurements
caught, because a control group that never catches anything is
still buying the number every other dashboard merely assumes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.content import digest_text
from forge.errors import Invalid


@dataclass
class ControlGroup:
    control_percent: int
    control_ticks: list[int] = field(default_factory=list)
    cached_ticks: list[int] = field(default_factory=list)
    control_digests: dict[str, str] = field(default_factory=dict)
    disagreements: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0 < self.control_percent <= 50:
            raise Invalid(
                "the control group is a slice, not a lifestyle: "
                "1 to 50 percent"
            )

    def is_control(self, build_id: str) -> bool:
        bucket = int(digest_text(build_id)[:8], 16) % 100
        return bucket < self.control_percent

    def record_build(
        self,
        build_id: str,
        wall_ticks: int,
        output_digest: str,
        key: str,
    ) -> str:
        if wall_ticks <= 0:
            raise Invalid("a build takes time")
        if self.is_control(build_id):
            self.control_ticks.append(wall_ticks)
            self.control_digests[key] = output_digest
            return f"{build_id}: control, cold by design"
        self.cached_ticks.append(wall_ticks)
        truth = self.control_digests.get(key)
        if truth is not None and truth != output_digest:
            finding = (
                f"FAST AND WRONG: {key} cached "
                f"{output_digest[:8]} against control "
                f"{truth[:8]}"
            )
            self.disagreements.append(finding)
            return finding
        return f"{build_id}: cached"

    def speedup_report(self) -> str:
        if not self.control_ticks or not self.cached_ticks:
            raise Invalid(
                "the ratio needs both populations; run more "
                "builds"
            )
        control_mean = sum(self.control_ticks) / len(
            self.control_ticks
        )
        cached_mean = sum(self.cached_ticks) / len(
            self.cached_ticks
        )
        ratio = control_mean / cached_mean
        cost = sum(self.control_ticks)
        line = (
            f"measured speedup {ratio:.1f}x "
            f"({control_mean:.0f} cold against "
            f"{cached_mean:.0f} cached), paid for with "
            f"{cost} control tick(s)"
        )
        if self.disagreements:
            line += (
                f"; and the control caught "
                f"{len(self.disagreements)} fast-and-wrong "
                "result(s), which repays every tick"
            )
        return line
