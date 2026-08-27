"""The bill of materials: what shipped, from where, under which terms.

The provenance manifest knows what built the binary; the license
aspect knows the terms each component carries; the lockfile knows
the external versions. The SBOM is the treaty document that joins
them for the reader who has none of that context: one entry per
component naming its version, its content digest, its license,
and whether it is first-party or pulled from outside, folded into
a document digest so two SBOMs compare as strings. Completeness
is checked, not assumed: a component in the build without an SBOM
entry fails the export by name, because a bill of materials with
missing lines is not a shorter bill, it is a different document
pretending, and the security questionnaire it gets pasted into
does not have a column for "probably".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.content import digest_text
from forge.errors import Invalid, Missing


@dataclass(frozen=True)
class BomEntry:
    component: str
    version: str
    digest: str
    license_name: str
    origin: str

    def line(self) -> str:
        return (
            f"{self.component} {self.version} [{self.license_name}] "
            f"({self.origin}) {self.digest}"
        )


@dataclass
class BillOfMaterials:
    entries: dict[str, BomEntry] = field(default_factory=dict)

    def add(self, entry: BomEntry) -> None:
        if entry.origin not in ("first-party", "external"):
            raise Invalid(
                f"{entry.component}: origin must be first-party or "
                f"external"
            )
        if entry.component in self.entries:
            raise Invalid(
                f"{entry.component} is already on the bill"
            )
        self.entries[entry.component] = entry

    def check_complete(self, built_components: set[str]) -> None:
        missing = sorted(built_components - set(self.entries))
        if missing:
            raise Missing(
                f"the build contains {missing} with no SBOM entry; a "
                f"bill with missing lines is a different document "
                f"pretending"
            )

    def export(self, built_components: set[str]) -> str:
        self.check_complete(built_components)
        lines = [
            self.entries[name].line()
            for name in sorted(self.entries)
        ]
        body = "\n".join(lines)
        stamp = digest_text(body)
        return f"sbom {stamp}\n{body}"

    def externals(self) -> list[str]:
        return sorted(
            name
            for name, entry in self.entries.items()
            if entry.origin == "external"
        )

    def license_summary(self) -> str:
        by_license: dict[str, int] = {}
        for entry in self.entries.values():
            by_license[entry.license_name] = (
                by_license.get(entry.license_name, 0) + 1
            )
        return ", ".join(
            f"{name}: {count}"
            for name, count in sorted(by_license.items())
        )
