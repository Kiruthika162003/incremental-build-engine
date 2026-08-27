"""Memory overcommit: promises exceed the machine, statistics signs the lease.

Actions declare their peak memory and rarely touch it, so a
worker that only accepts declared-sum-fits work runs half
empty. Overcommit rents the same physical RAM to more actions
on the bet that peaks will not align, and the bet has a
correct size: the safe ratio comes from the workload's typical
concurrent usage, not from optimism, and the model prices both
failure directions. Undercommitting wastes quiet gigabytes all
year; overcommitting works beautifully until the correlated
day, the release build that starts every linker at once, when
peaks align by construction and the OOM killer chooses a
victim nobody nominated. The planner therefore takes the
workload's worst observed alignment as its floor, not its
tail, because the correlated day is not a tail event, it is a
calendar event, and calendars repeat.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid


@dataclass(frozen=True)
class MemoryDay:
    label: str
    declared_sum: int
    peak_concurrent_use: int

    def __post_init__(self) -> None:
        if self.peak_concurrent_use > self.declared_sum:
            raise Invalid(
                f"{self.label}: usage above declarations means "
                "the declarations are lies, which is a "
                "different module's problem"
            )


def safe_ratio(
    physical_ram: int, days: list[MemoryDay]
) -> float:
    if not days:
        raise Invalid("no observed days, no statistics, no lease")
    worst = max(day.peak_concurrent_use for day in days)
    if worst == 0:
        raise Invalid("a workload that never used memory is idle")
    return physical_ram / worst


def lease_plan(
    physical_ram: int, days: list[MemoryDay]
) -> str:
    ratio = safe_ratio(physical_ram, days)
    worst_day = max(
        days, key=lambda day: day.peak_concurrent_use
    )
    committable = int(physical_ram * ratio)
    lines = [
        f"physical {physical_ram}, worst observed alignment "
        f"{worst_day.peak_concurrent_use} on {worst_day.label}: "
        f"commit up to {committable} declared "
        f"({ratio:.1f}x)"
    ]
    if ratio < 1.5:
        lines.append(
            f"  the floor is {worst_day.label}, not the "
            "average day: the correlated day is a calendar "
            "event, and calendars repeat"
        )
    else:
        lines.append(
            "  quiet gigabytes recovered; undercommitting "
            "wastes them all year"
        )
    return "\n".join(lines)


def oom_postmortem(
    physical_ram: int, day: MemoryDay, ratio_used: float
) -> str:
    committed = int(physical_ram * ratio_used)
    if day.peak_concurrent_use <= physical_ram:
        return (
            f"{day.label}: peaks stayed under physical RAM; "
            "the bet held"
        )
    return (
        f"{day.label}: {committed} was promised against "
        f"{physical_ram} physical and the aligned peak hit "
        f"{day.peak_concurrent_use}; the OOM killer chose a "
        "victim nobody nominated, and the ratio was sized on "
        "optimism instead of on this exact day"
    )
