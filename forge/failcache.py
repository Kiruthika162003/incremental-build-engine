"""Caching failures: a red build should not re-fail expensively all morning.

Success caching is obvious; failure caching is the contested
half. During triage a broken action gets asked for a dozen times
an hour, and re-running a ninety-tick compile to reproduce the
same error message is a tax on everyone downstream of the
breakage. The failure cache stores the error against the same
content key as a success would use, so the fix busts the entry
automatically, new inputs, new key, no staleness policy needed.
The guard is against the real hazard: caching a flaky failure
converts an occasional annoyance into a permanent lie, so only
failures certified deterministic, reproduced twice on the same
key, are admitted, and an uncertified failure is served fresh
every time with the certification cost metered. The ledger
reports ticks saved by served failures next to ticks spent
certifying, because the policy is a purchase and the receipts
settle whether it was a good one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class FailureCache:
    certified: dict[str, str] = field(default_factory=dict)
    first_sightings: dict[str, str] = field(default_factory=dict)
    served: int = 0
    ticks_saved: int = 0
    certification_ticks: int = 0

    def lookup(self, key: str, run_ticks: int) -> str | None:
        if key in self.certified:
            self.served += 1
            self.ticks_saved += run_ticks
            return (
                f"cached failure ({self.certified[key]}); the "
                "fix will mint a new key and bust this entry"
            )
        return None

    def report_failure(
        self, key: str, error: str, run_ticks: int
    ) -> str:
        if not error.strip():
            raise Invalid("a failure needs its error message")
        if key in self.certified:
            return "already certified; lookup should have served it"
        seen = self.first_sightings.get(key)
        if seen is None:
            self.first_sightings[key] = error
            return (
                "first sighting recorded; one reproduction "
                "away from certification"
            )
        self.certification_ticks += run_ticks
        if seen == error:
            self.certified[key] = error
            del self.first_sightings[key]
            return (
                "certified deterministic: reproduced twice on "
                "one key, now served from cache"
            )
        del self.first_sightings[key]
        return (
            "REFUSED: the same key failed two different ways; "
            "that is flakiness, and caching it would make an "
            "occasional annoyance a permanent lie"
        )

    def ledger(self) -> str:
        return (
            f"{self.served} failure(s) served, "
            f"{self.ticks_saved} tick(s) saved, "
            f"{self.certification_ticks} spent certifying, "
            f"{len(self.certified)} certified entrie(s)"
        )
