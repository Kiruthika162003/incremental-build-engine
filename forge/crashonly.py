"""Crash-only design: the only shutdown that always works is the one you test.

Graceful shutdown is a gift the infrastructure sometimes
gives; kill -9 is the shutdown the power cord guarantees, and
a component correct only when shut down politely is a
component that corrupts on the day the politeness is skipped.
The auditor grades each component's recovery story: crash-safe
means its state survives an ungraceful end through journals,
atomic renames, or idempotent replay, and the mechanism is
named; graceful-only means its correctness depends on a
shutdown hook running, and the audit says what breaks when it
does not. The doctrine has a corollary the report enforces:
a crash-safe component's graceful path should be a
convenience, faster or quieter, never a correctness
requirement, so any component whose shutdown hook does more
than hurry is flagged, because work that must happen at
shutdown is work that must actually happen at startup, after
the crash that skipped it.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid

MECHANISMS = (
    "journal-replay",
    "atomic-rename",
    "idempotent-replay",
    "stateless",
)


@dataclass(frozen=True)
class Component:
    name: str
    recovery_mechanism: str | None
    shutdown_hook_does: str

    def crash_safe(self) -> bool:
        return self.recovery_mechanism in MECHANISMS


def grade(component: Component) -> str:
    if component.crash_safe():
        verdict = (
            f"{component.name}: crash-safe via "
            f"{component.recovery_mechanism}"
        )
        if component.shutdown_hook_does not in (
            "nothing",
            "hurry",
        ):
            verdict += (
                f"; FLAG: its hook does "
                f"'{component.shutdown_hook_does}', and work "
                "that must happen at shutdown is work that "
                "must actually happen at startup, after the "
                "crash that skipped it"
            )
        return verdict
    if component.recovery_mechanism is not None:
        raise Invalid(
            f"{component.name} claims unknown mechanism "
            f"{component.recovery_mechanism}"
        )
    return (
        f"{component.name}: GRACEFUL-ONLY; correctness "
        f"depends on '{component.shutdown_hook_does}' "
        "running, and the power cord does not call hooks"
    )


def fleet_audit(components: list[Component]) -> str:
    if not components:
        raise Invalid("no components to audit")
    graded = [grade(component) for component in components]
    unsafe = sum(
        1 for line in graded if "GRACEFUL-ONLY" in line
    )
    flagged = sum(1 for line in graded if "FLAG:" in line)
    lines = [
        f"{len(components) - unsafe} crash-safe, {unsafe} "
        f"graceful-only, {flagged} hook(s) doing correctness "
        "work"
    ]
    lines.extend(f"  {line}" for line in graded)
    if unsafe == 0 and flagged == 0:
        lines.append(
            "kill -9 is a supported shutdown everywhere; the "
            "power cord holds no surprises"
        )
    return "\n".join(lines)
