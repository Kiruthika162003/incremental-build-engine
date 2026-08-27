"""The weekly digest: sections that earn their place or stay home.

The platform's organs each produce a ledger line, and the
digest's whole craft is refusal: a section appears only when
its week had something to say, empty sections are omitted
rather than padded, and the ordering is severity-first so the
reader who stops after two paragraphs stops informed. Every
section names its source organ, because a digest line nobody
can trace to a meter is a rumor with formatting, and the
closing line counts what was omitted, since "three quiet
sections" is itself information, the good kind, and hiding
the quiet weeks makes the loud ones read as normal. The
digest refuses to ship empty outright: a week where every
organ was quiet produces the one-line version, all quiet,
which respects the reader more than a page of padding ever
could.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

SEVERITIES = ("incident", "warning", "info")


@dataclass
class WeeklyDigest:
    sections: list[tuple[str, str, str, str]] = field(
        default_factory=list
    )
    omitted: int = 0

    def add_section(
        self,
        severity: str,
        source_organ: str,
        title: str,
        body: str,
    ) -> None:
        if severity not in SEVERITIES:
            raise Invalid(f"unknown severity {severity}")
        if not source_organ.strip():
            raise Invalid(
                "a digest line nobody can trace to a meter is "
                "a rumor with formatting"
            )
        if not body.strip():
            self.omitted += 1
            return
        self.sections.append(
            (severity, source_organ, title, body)
        )

    def render(self) -> str:
        if not self.sections:
            return (
                f"all quiet ({self.omitted} organ(s) with "
                "nothing to say, which respects the reader "
                "more than padding)"
            )
        ordered = sorted(
            self.sections,
            key=lambda section: SEVERITIES.index(section[0]),
        )
        lines = []
        for severity, organ, title, body in ordered:
            lines.append(
                f"[{severity}] {title} (per {organ})"
            )
            lines.append(f"  {body}")
        lines.append(
            f"{self.omitted} quiet section(s) omitted; the "
            "quiet weeks are what make the loud ones legible"
        )
        return "\n".join(lines)
