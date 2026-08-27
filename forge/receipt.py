"""The build receipt: what you got, what it cost, who paid.

Developers distrust build systems they cannot read, and the
raw report is written for operators: hits, misses, cutoffs,
freight. The receipt translates one build into the three
numbers a developer actually owns, what ran, what the caches
and cutoffs saved them, and how long they personally waited,
with the farm's own spend printed separately, because "the
farm paid 120 ticks so you waited 8" is the sentence that
builds trust in shared infrastructure, and hiding the farm's
side of the bill is how developers conclude the farm does
nothing. The receipt refuses to editorialize: a slow build
with honest numbers reads better than a fast one with vague
ones, and the itemized savings line only lists mechanisms that
actually contributed this build, since a receipt padded with
zero-dollar line items reads as marketing.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid


@dataclass(frozen=True)
class BuildFacts:
    targets_ran: int
    cache_hits: int
    cutoff_skips: int
    interface_skips: int
    farm_ticks: int
    developer_wait_ticks: int

    def __post_init__(self) -> None:
        if self.developer_wait_ticks > self.farm_ticks and (
            self.farm_ticks > 0
        ):
            raise Invalid(
                "the developer cannot wait longer than the "
                "farm worked; someone's clock is lying"
            )
        if min(
            self.targets_ran,
            self.cache_hits,
            self.cutoff_skips,
            self.interface_skips,
            self.farm_ticks,
            self.developer_wait_ticks,
        ) < 0:
            raise Invalid("receipt numbers cannot be negative")


def receipt(facts: BuildFacts) -> str:
    total_avoided = (
        facts.cache_hits
        + facts.cutoff_skips
        + facts.interface_skips
    )
    lines = [
        f"ran {facts.targets_ran}, avoided {total_avoided}"
    ]
    savings = []
    if facts.cache_hits:
        savings.append(f"cache {facts.cache_hits}")
    if facts.cutoff_skips:
        savings.append(f"early cutoff {facts.cutoff_skips}")
    if facts.interface_skips:
        savings.append(
            f"interface cutoff {facts.interface_skips}"
        )
    if savings:
        lines.append(f"  saved by: {', '.join(savings)}")
    if facts.farm_ticks:
        lines.append(
            f"  the farm paid {facts.farm_ticks} tick(s) so "
            f"you waited {facts.developer_wait_ticks}"
        )
    else:
        lines.append(
            f"  everything local: you waited "
            f"{facts.developer_wait_ticks} tick(s)"
        )
    if facts.targets_ran == 0 and total_avoided == 0:
        raise Invalid(
            "a build that neither ran nor avoided anything "
            "did not happen"
        )
    return "\n".join(lines)
