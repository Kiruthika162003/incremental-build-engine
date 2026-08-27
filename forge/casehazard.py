"""Case hazards: two names that Windows thinks are one file.

A repo developed on Linux can carry README.md and readme.md as
two files for years, and the first Windows or macOS checkout
folds them into one, silently, with whichever content the
checkout wrote last. The detector folds every declared path to
its casefolded form and names each collision with all of its
spellings, because the fix is a rename and the rename needs the
list. Outputs get the stricter rule: a build that would write
two outputs differing only in case is refused before it runs
anywhere, not warned, since an artifact tree that works on the
build farm and corrupts on a laptop is the kind of portability
bug that costs a week precisely because nothing errors. Near
misses are reported at a lower temperature: paths differing
only in case from a directory, spelling drift like Util and
util, which are legal today and a collision after the next
refactor.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid


@dataclass
class CaseAuditor:
    source_paths: tuple[str, ...]
    output_paths: tuple[str, ...]

    def _collisions(
        self, paths: tuple[str, ...]
    ) -> list[list[str]]:
        folded: dict[str, list[str]] = {}
        for path in paths:
            folded.setdefault(path.casefold(), []).append(path)
        return [
            sorted(spellings)
            for _, spellings in sorted(folded.items())
            if len(spellings) > 1
        ]

    def source_report(self) -> str:
        collisions = self._collisions(self.source_paths)
        if not collisions:
            return "sources are case-clean on every filesystem"
        lines = [
            f"{len(collisions)} source collision(s); the fix "
            "is a rename and this is the list"
        ]
        for spellings in collisions:
            lines.append(
                f"  {' / '.join(spellings)} fold into one file "
                "on Windows and macOS"
            )
        return "\n".join(lines)

    def check_outputs(self) -> str:
        collisions = self._collisions(self.output_paths)
        if collisions:
            named = "; ".join(
                " / ".join(spellings)
                for spellings in collisions
            )
            raise Invalid(
                f"output case collision: {named}; an artifact "
                "tree that works on the farm and corrupts on a "
                "laptop costs a week because nothing errors"
            )
        return (
            f"{len(self.output_paths)} output(s) case-clean"
        )

    def drift_watch(self) -> list[str]:
        directories: dict[str, set[str]] = {}
        for path in self.source_paths:
            ancestor = path
            while "/" in ancestor:
                ancestor = ancestor.rsplit("/", 1)[0]
                directories.setdefault(
                    ancestor.casefold(), set()
                ).add(ancestor)
        return sorted(
            f"{' / '.join(sorted(spellings))}: one directory "
            "today by luck, a collision after the next refactor"
            for spellings in directories.values()
            if len(spellings) > 1
        )
