"""Importing Makefiles: the migration walks in, it does not leap.

Nobody rewrites four hundred Makefile rules by hand, so the
importer reads the subset of make that build files actually use,
targets, prerequisites, and one-line recipes, and emits the
equivalent stanzas with the recipe's first word as the command.
The subset is enforced, not assumed: variables, pattern rules,
and multi-line recipes are refused with the line number and a
sentence about why, because silently mistranslating a pattern
rule produces a build that works differently rather than not at
all, and different-not-broken is the worst migration outcome. The
import report grades the file, how many rules translated clean
and which lines need a human, so the migration has a progress
number instead of a feeling, and phony targets are recognised and
dropped with a note since aggregation is the graph's job now.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.buildfile import BuildFile, Stanza
from forge.errors import Invalid

UNSUPPORTED_MARKS = ("%", "$(", "${")


@dataclass
class ImportReport:
    translated: list[str] = field(default_factory=list)
    needs_a_human: list[str] = field(default_factory=list)
    phony_dropped: list[str] = field(default_factory=list)

    def grade(self) -> str:
        total = len(self.translated) + len(self.needs_a_human)
        if total == 0:
            return "nothing to import"
        share = len(self.translated) / total
        return (
            f"{len(self.translated)}/{total} rules translated clean "
            f"({share:.0%}); {len(self.needs_a_human)} need a human, "
            f"{len(self.phony_dropped)} phony targets dropped"
        )


def import_makefile(text: str) -> tuple[BuildFile, ImportReport]:
    parsed = BuildFile()
    report = ImportReport()
    lines = text.splitlines()
    phony: set[str] = set()
    index = 0
    while index < len(lines):
        raw = lines[index]
        line = raw.split("#", 1)[0].rstrip()
        index += 1
        if not line.strip():
            continue
        if line.startswith(".PHONY:"):
            phony.update(line.split(":", 1)[1].split())
            continue
        if line.startswith("\t"):
            raise Invalid(
                f"line {index}: a recipe with no rule above it"
            )
        if ":" not in line:
            report.needs_a_human.append(
                f"line {index}: not a rule ({line.strip()!r})"
            )
            continue
        target_part, _, prereq_part = line.partition(":")
        target = target_part.strip()
        if any(mark in line for mark in UNSUPPORTED_MARKS):
            report.needs_a_human.append(
                f"line {index}: {target} uses patterns or variables; "
                f"mistranslating those makes a build that works "
                f"differently, which is worse than broken"
            )
            while index < len(lines) and lines[index].startswith("\t"):
                index += 1
            continue
        recipe_lines = []
        while index < len(lines) and lines[index].startswith("\t"):
            recipe_lines.append(lines[index].strip())
            index += 1
        if target in phony:
            report.phony_dropped.append(target)
            continue
        if len(recipe_lines) != 1:
            report.needs_a_human.append(
                f"line {index}: {target} has "
                f"{len(recipe_lines)} recipe lines; the subset "
                f"takes exactly one"
            )
            continue
        prerequisites = tuple(prereq_part.split())
        parsed.stanzas[target] = Stanza(
            name=target,
            command=recipe_lines[0],
            reads=prerequisites,
            writes=(target,),
            needs=prerequisites,
            line=index,
        )
        report.translated.append(target)
    for stanza in parsed.stanzas.values():
        for need in stanza.needs:
            if (
                need not in parsed.stanzas
                and need not in parsed.sources
            ):
                parsed.sources.append(need)
    return parsed, report
