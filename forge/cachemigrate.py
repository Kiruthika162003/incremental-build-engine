"""Cache format migrations: upgrade the shelf without burning the library.

Cache entry formats change, a field added, a digest widened, and
the lazy migration is to bump the version and let a full farm's
worth of warm state evaporate, which taxes every developer for
the schema's convenience. The migrator walks the old shelf entry
by entry: entries it can mechanically upgrade are rewritten in
the new format and keep their warmth, entries the new format
cannot represent are dropped with the specific reason, and
nothing is dropped silently, because the difference between an
upgrade and an outage is an accounting of what did not survive.
The dry run is half the tool: the same walk with the writes
withheld prints what would survive before anyone commits, and a
migration whose dry run predicts heavy loss is a schema change
that should pay for a translator, not a farm that should pay
for a cold morning.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from forge.errors import Invalid

Upgrader = Callable[[dict], dict | str]


@dataclass
class CacheMigrator:
    upgrade: Upgrader
    migrated: dict[str, dict] = field(default_factory=dict)
    dropped: list[str] = field(default_factory=list)

    def run(
        self, shelf: dict[str, dict], dry_run: bool = False
    ) -> str:
        if not shelf:
            raise Invalid("an empty shelf needs no migration")
        survived = 0
        losses = []
        for key in sorted(shelf):
            outcome = self.upgrade(dict(shelf[key]))
            if isinstance(outcome, dict):
                survived += 1
                if not dry_run:
                    self.migrated[key] = outcome
            else:
                losses.append(f"{key}: {outcome}")
                if not dry_run:
                    self.dropped.append(f"{key}: {outcome}")
        share = survived / len(shelf)
        mode = "dry run: " if dry_run else ""
        lines = [
            f"{mode}{survived} of {len(shelf)} entrie(s) "
            f"survive ({share:.0%})"
        ]
        lines.extend(f"  dropped {loss}" for loss in losses)
        if dry_run and share < 0.5:
            lines.append(
                "  heavy loss predicted: this schema change "
                "should pay for a translator, not the farm for "
                "a cold morning"
            )
        return "\n".join(lines)
