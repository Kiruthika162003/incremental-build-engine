"""The watch budget: the kernel lends only so many eyes.

File watching feels free until the checkout outgrows the
kernel's watch limit, and then somebody's watcher silently
stops seeing a directory, which is the worst failure mode a
watcher can have: not slow, blind. The budget makes the limit
a decision instead of a surprise: directories are ranked by
their measured change rate, the watch allowance goes to the
busiest until it runs out, and the remainder is explicitly
demoted to polling with an interval derived from how rarely it
changes, so cold directories are checked lazily rather than
unwatched accidentally. The report names the split and its
worst case, the coldest watched directory against the hottest
polled one, because that boundary pair is where the next
misfiled directory will hurt, and reviewing it beats
rediscovering it.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid

POLL_BASE_TICKS = 20


@dataclass(frozen=True)
class WatchedDir:
    path: str
    changes_per_day: int

    def __post_init__(self) -> None:
        if self.changes_per_day < 0:
            raise Invalid(
                f"{self.path}: change rates cannot be negative"
            )


def plan(
    directories: list[WatchedDir], watch_limit: int
) -> str:
    if not directories:
        raise Invalid("nothing to watch")
    if watch_limit < 1:
        raise Invalid(
            "a zero watch limit means polling everything; "
            "that is a plan, not a budget"
        )
    ranked = sorted(
        directories,
        key=lambda held: (-held.changes_per_day, held.path),
    )
    watched = ranked[:watch_limit]
    polled = ranked[watch_limit:]
    lines = [
        f"{len(watched)} watched, {len(polled)} polled; the "
        "kernel lends only so many eyes"
    ]
    for directory in polled:
        interval = POLL_BASE_TICKS + (
            POLL_BASE_TICKS
            * 10
            // max(directory.changes_per_day, 1)
        )
        lines.append(
            f"  poll {directory.path} every {interval} tick(s) "
            f"({directory.changes_per_day} change(s)/day)"
        )
    if polled and watched:
        boundary_watched = watched[-1]
        boundary_polled = polled[0]
        lines.append(
            f"  boundary: {boundary_watched.path} "
            f"({boundary_watched.changes_per_day}/day) is the "
            f"coldest watched; {boundary_polled.path} "
            f"({boundary_polled.changes_per_day}/day) is the "
            "hottest polled; review this pair before it "
            "reviews you"
        )
    return "\n".join(lines)


def blindness_check(
    directories: list[WatchedDir],
    watch_limit: int,
    actually_watched: set[str],
) -> str:
    ranked = sorted(
        directories,
        key=lambda held: (-held.changes_per_day, held.path),
    )
    should_watch = {
        directory.path
        for directory in ranked[:watch_limit]
    }
    silently_blind = sorted(should_watch - actually_watched)
    if silently_blind:
        return (
            f"BLIND: {', '.join(silently_blind)} should be "
            "watched and are not; not slow, blind, which is "
            "the worst failure a watcher can have"
        )
    return "every budgeted watch is live"
