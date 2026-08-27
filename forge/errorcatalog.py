"""The error catalog: every diagnostic has a number, a fix, and a count.

Free-text errors cannot be counted, and what cannot be counted
cannot be prioritised: the same confusing failure bites forty
developers as forty unrelated bad afternoons. The catalog assigns
each diagnostic a stable code, a one-line explanation, and where
one exists, a mechanical fix-it, and every emission is tallied so
the weekly report ranks confusion by frequency. The ranking is
the tool's whole politics: the error worth rewriting is the one
emitted four hundred times, not the one the loudest person hit,
and the fix-it coverage line, what share of emissions carried a
mechanical fix, is the score for how often the tool did the work
instead of assigning it. Unknown codes are refused at emission,
because an uncatalogued error is exactly the free text this
module exists to end.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass(frozen=True)
class Diagnostic:
    code: str
    explanation: str
    fixit: str | None = None


@dataclass
class ErrorCatalog:
    diagnostics: dict[str, Diagnostic] = field(default_factory=dict)
    emissions: dict[str, int] = field(default_factory=dict)

    def register(self, diagnostic: Diagnostic) -> None:
        if diagnostic.code in self.diagnostics:
            raise Invalid(f"{diagnostic.code} is already catalogued")
        if not diagnostic.explanation.strip():
            raise Invalid(
                f"{diagnostic.code} without an explanation is a "
                f"number wearing a trench coat"
            )
        self.diagnostics[diagnostic.code] = diagnostic

    def emit(self, code: str, context: str) -> str:
        held = self.diagnostics.get(code)
        if held is None:
            raise Invalid(
                f"uncatalogued error {code}; free text is what this "
                f"catalog exists to end"
            )
        self.emissions[code] = self.emissions.get(code, 0) + 1
        line = f"[{code}] {held.explanation}: {context}"
        if held.fixit:
            line += f" (fix: {held.fixit})"
        return line

    def weekly_report(self) -> str:
        if not self.emissions:
            return "no errors emitted; a quiet week or a broken tally"
        ranked = sorted(
            self.emissions.items(), key=lambda row: (-row[1], row[0])
        )
        lines = [
            f"{code}: {count} emissions"
            + (
                ""
                if self.diagnostics[code].fixit
                else " [no mechanical fix; a rewrite candidate]"
            )
            for code, count in ranked
        ]
        total = sum(self.emissions.values())
        with_fix = sum(
            count
            for code, count in self.emissions.items()
            if self.diagnostics[code].fixit
        )
        lines.append(
            f"fix-it coverage: {with_fix}/{total} emissions carried "
            f"a mechanical fix ({with_fix / total:.0%})"
        )
        return "\n".join(lines)

    def rewrite_candidate(self) -> str | None:
        fixless = [
            (count, code)
            for code, count in self.emissions.items()
            if not self.diagnostics[code].fixit
        ]
        if not fixless:
            return None
        count, code = max(fixless)
        return (
            f"{code} bit {count} times with no mechanical fix; "
            f"rewrite this one first"
        )
