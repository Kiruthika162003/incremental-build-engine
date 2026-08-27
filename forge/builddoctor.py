"""The build doctor: the BUILD file drifts, the doctor writes the diff.

Declarations rot in both directions as code moves: the needs line
keeps a dependency the last refactor orphaned, and misses one the
new include quietly demands through the scanner's early warning.
The doctor reconciles three testimonies, what the BUILD file
declares, what the scanner reads from the source text, and what
observed execution actually touched, and writes its prescription
as exact edits: add these needs, drop those, with the testimony
that justifies each line. Observation outranks scanning when they
disagree, because the scanner sees the disabled branch, and the
prescription never auto-applies, since the doctor can read the
graph but only the owner knows whether the odd dependency is load
bearing for a reason no analysis sees. The clinic report counts
prescriptions by package, and the package that tops the list
every week has a rot process, not a rot incident.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Prescription:
    target: str
    add: list[tuple[str, str]] = field(default_factory=list)
    drop: list[tuple[str, str]] = field(default_factory=list)

    def healthy(self) -> bool:
        return not self.add and not self.drop

    def page(self) -> str:
        if self.healthy():
            return f"{self.target}: the declaration matches reality"
        lines = [f"{self.target}:"]
        for need, testimony in self.add:
            lines.append(f"  add needs = {need} ({testimony})")
        for need, testimony in self.drop:
            lines.append(f"  drop needs = {need} ({testimony})")
        return "\n".join(lines)


def diagnose(
    target: str,
    declared: set[str],
    scanned: set[str],
    observed: set[str] | None,
) -> Prescription:
    truth = observed if observed is not None else scanned
    basis = (
        "observed at run time"
        if observed is not None
        else "scanned from the source"
    )
    prescription = Prescription(target=target)
    for need in sorted(truth - declared):
        prescription.add.append((need, basis))
    for need in sorted(declared - truth):
        if observed is not None and need in scanned:
            prescription.drop.append(
                (
                    need,
                    "scanned but never touched at run time; likely "
                    "a disabled branch",
                )
            )
        else:
            prescription.drop.append(
                (need, "neither scanned nor observed")
            )
    return prescription


@dataclass
class Clinic:
    visits: dict[str, int] = field(default_factory=dict)

    def file_visit(self, prescription: Prescription) -> None:
        if prescription.healthy():
            return
        package = (
            prescription.target.rsplit("/", 1)[0]
            if "/" in prescription.target
            else ""
        )
        self.visits[package] = self.visits.get(package, 0) + 1

    def report(self) -> str:
        if not self.visits:
            return "no prescriptions; the declarations hold"
        ranked = sorted(
            self.visits.items(), key=lambda row: (-row[1], row[0])
        )
        lines = [
            f"{package or 'the root'}: {count} prescriptions"
            for package, count in ranked
        ]
        top = ranked[0]
        if top[1] >= 3:
            lines.append(
                f"{top[0]} tops the list; that is a rot process, "
                f"not a rot incident"
            )
        return "\n".join(lines)
