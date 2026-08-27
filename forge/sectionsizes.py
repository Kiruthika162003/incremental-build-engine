"""Section attribution: the binary grew, and the section names the suspect.

A size budget flags that the binary grew; the section breakdown
says where, and where is most of the diagnosis: growth in .text
is code somebody wrote, growth in .data is a table somebody
embedded, growth in .debug is a flag somebody flipped, and the
three suspects live in different reviews. The tracker records
per-section bytes per build, the delta report names the section
that moved with its share of the total growth, and the classic
false alarm is caught by arithmetic: a binary that grew only in
.debug did not get slower to load or bigger to ship after
stripping, and the report says exactly that instead of paging the
performance channel over symbols. Unknown sections are carried,
not refused, because toolchains invent sections and a tracker
that only knows last year's names goes quietly blind.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

STRIPPED_SECTIONS = (".debug", ".comment")


@dataclass
class SectionTracker:
    history: list[dict[str, int]] = field(default_factory=list)

    def record(self, sections: dict[str, int]) -> None:
        if any(size < 0 for size in sections.values()):
            raise Invalid("section sizes cannot be negative")
        self.history.append(dict(sections))

    def delta_report(self) -> str:
        if len(self.history) < 2:
            raise Invalid("a delta needs two builds")
        before = self.history[-2]
        after = self.history[-1]
        deltas = {}
        for section in sorted(set(before) | set(after)):
            moved = after.get(section, 0) - before.get(section, 0)
            if moved:
                deltas[section] = moved
        if not deltas:
            return "no section moved; the binary is byte-stable"
        total_growth = sum(
            moved for moved in deltas.values() if moved > 0
        )
        lines = []
        for section, moved in sorted(
            deltas.items(), key=lambda row: -abs(row[1])
        ):
            share = (
                f" ({moved / total_growth:.0%} of the growth)"
                if moved > 0 and total_growth
                else ""
            )
            lines.append(f"{section}: {moved:+}{share}")
        shipped_growth = sum(
            moved
            for section, moved in deltas.items()
            if moved > 0
            and not section.startswith(STRIPPED_SECTIONS)
        )
        if total_growth and shipped_growth == 0:
            lines.append(
                "all growth strips out before shipping; do not page "
                "the performance channel over symbols"
            )
        return "\n".join(lines)

    def shipped_size(self) -> int:
        if not self.history:
            raise Invalid("nothing recorded")
        return sum(
            size
            for section, size in self.history[-1].items()
            if not section.startswith(STRIPPED_SECTIONS)
        )
