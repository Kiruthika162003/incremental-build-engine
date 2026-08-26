"""An audit is a rebuilt scenario with its numbers pinned to the page.

Each audit module exposes run() returning a Finding: the claim the
scenario supports, the measurements behind it, and whether the
checks that make the claim true still pass. The style rule carried
from the sibling repositories holds here: when a guess was wrong,
the docstring keeps the guess beside the measured truth, because
the distance between them is the finding. A Finding whose checks
fail is rendered, not hidden; a broken expectation is the most
informative thing an audit can produce.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Finding:
    audit: str
    claim: str
    numbers: dict = field(default_factory=dict)
    holds: bool = True

    def line(self) -> str:
        mark = "holds" if self.holds else "BROKEN"
        shown = ", ".join(
            f"{key}={value}" for key, value in sorted(self.numbers.items())
        )
        return f"{self.audit}: {self.claim} [{mark}] ({shown})"
