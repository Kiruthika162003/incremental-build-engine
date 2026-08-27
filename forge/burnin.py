"""Worker burn-in: prove yourself on known bytes before touching real work.

A new machine joining the farm is a hypothesis, not a worker:
its compiler might be a point release off, its filesystem might
fold case, its RAM might be quietly failing at one address in a
billion. The burn-in hands the candidate a probe set of actions
whose digests the farm already knows cold, and admission is
exact: every probe must reproduce its known digest, and one
mismatch rejects the machine with the probe named, because a
worker that gets one known answer wrong will get unknown
answers wrong at a rate nobody can measure. Flaky probes are
the rig's own overhead and are handled by the same rule run
twice: a probe that disagrees with itself disqualifies the
probe, not the machine, and it is pulled from the set with a
note, since a burn-in that fails good machines on its own bad
probe is a gate that teaches people to bypass gates.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from forge.errors import Invalid

RunProbe = Callable[[str, str], str]


@dataclass
class BurnInRig:
    known_digests: dict[str, str]
    run_probe: RunProbe
    retired_probes: list[str] = field(default_factory=list)
    admitted: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.known_digests:
            raise Invalid(
                "a burn-in with no probes admits anything"
            )

    def evaluate(self, worker: str) -> str:
        for probe in sorted(self.known_digests):
            if probe in self.retired_probes:
                continue
            expected = self.known_digests[probe]
            first = self.run_probe(worker, probe)
            if first == expected:
                continue
            second = self.run_probe(worker, probe)
            if second != first:
                self.retired_probes.append(probe)
                continue
            self.rejected.append(worker)
            return (
                f"{worker} REJECTED on {probe}: produced "
                f"{first[:8]} where the farm knows "
                f"{expected[:8]}; one wrong known answer means "
                "unknown answers wrong at an unmeasurable rate"
            )
        self.admitted.append(worker)
        live = len(self.known_digests) - len(self.retired_probes)
        return (
            f"{worker} admitted after {live} probe(s) "
            "reproduced cold"
        )

    def rig_report(self) -> str:
        lines = [
            f"{len(self.admitted)} admitted, "
            f"{len(self.rejected)} rejected, "
            f"{len(self.retired_probes)} probe(s) retired"
        ]
        for probe in self.retired_probes:
            lines.append(
                f"  retired {probe}: it disagreed with itself, "
                "which disqualifies the probe, not the machine"
            )
        return "\n".join(lines)
