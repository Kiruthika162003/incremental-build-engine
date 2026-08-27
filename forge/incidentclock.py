"""The incident clock: MTTR is three clocks wearing one acronym.

Time to resolve gets the headline, and the headline hides the
finding: an incident's duration splits into detection, how
long the failure ran before anyone knew, mitigation, how long
knowing took to stop the bleeding, and repair, how long the
real fix took after the pressure was off. The clock records
the four timestamps and attributes the total to its phases,
because the classic discovery, made once per organization and
then forgotten, is that detection dominates: the fix took
eleven minutes and finding out took three hours, which means
the investment belongs in monitoring, not in faster fixing.
The fleet report ranks phases by their share across incidents
and prescribes against the dominant one, since a team that
drills mitigation while detection eats eighty percent is
training for the wrong sport.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid


@dataclass(frozen=True)
class Incident:
    name: str
    began: int
    detected: int
    mitigated: int
    repaired: int

    def __post_init__(self) -> None:
        if not (
            self.began
            <= self.detected
            <= self.mitigated
            <= self.repaired
        ):
            raise Invalid(
                f"{self.name}: the clocks must be ordered "
                "began <= detected <= mitigated <= repaired"
            )

    def phases(self) -> dict[str, int]:
        return {
            "detection": self.detected - self.began,
            "mitigation": self.mitigated - self.detected,
            "repair": self.repaired - self.mitigated,
        }

    def story(self) -> str:
        split = self.phases()
        total = sum(split.values())
        if total == 0:
            return f"{self.name}: instantaneous, suspiciously"
        dominant = max(split, key=lambda phase: split[phase])
        return (
            f"{self.name}: {total} tick(s) total; detection "
            f"{split['detection']}, mitigation "
            f"{split['mitigation']}, repair "
            f"{split['repair']}; {dominant} dominated"
        )


def fleet_report(incidents: list[Incident]) -> str:
    if not incidents:
        raise Invalid("no incidents; enjoy it while it lasts")
    totals = {"detection": 0, "mitigation": 0, "repair": 0}
    for incident in incidents:
        for phase, ticks in incident.phases().items():
            totals[phase] += ticks
    grand = sum(totals.values())
    lines = [f"{len(incidents)} incident(s), {grand} tick(s)"]
    for phase in sorted(
        totals, key=lambda held: -totals[held]
    ):
        share = 100 * totals[phase] // max(grand, 1)
        lines.append(f"  {phase}: {totals[phase]} ({share}%)")
    dominant = max(totals, key=lambda held: totals[held])
    if totals[dominant] * 2 > grand:
        prescription = {
            "detection": "the investment belongs in monitoring",
            "mitigation": "drill the first fifteen minutes",
            "repair": "the fixes are hard; invest in prevention",
        }[dominant]
        lines.append(
            f"  {dominant} eats more than half: "
            f"{prescription}, because training the other "
            "phases is training for the wrong sport"
        )
    return "\n".join(lines)
