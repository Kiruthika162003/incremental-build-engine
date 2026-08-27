"""The gate reads this repository's own audits page, live.

The ship gate's first check is "audits clean", and this drill
refuses to fake it: it calls the audit registry the CLI calls,
counts the findings and the broken among them, and feeds the
real number into a real gate alongside an error budget still
in the black and a clean room with its trust renewed. The go
that comes back is therefore partly about this repository:
if any audit in this file's own registry breaks, this drill
breaks with it, which makes the gate check the one audit that
audits the auditors. The second scenario freezes the budget
and confirms the no-go names the blocker, because a gate
proven only on sunny days is a light, and the whole page
exists because the gate reads sentences.
"""

from __future__ import annotations

import importlib

from forge.audits import registry
from forge.audits.finding import Finding
from forge.errorbudget import ErrorBudget
from forge.shipgate import ShipGate


def run() -> Finding:
    findings = [
        module_name
        for module_name in registry.AUDITS
        if module_name != "forge.audits.gatecheck"
    ]
    broken = 0
    for dotted in findings:
        module = importlib.import_module(dotted)
        if not module.run().holds:
            broken += 1
    budget = ErrorBudget(
        window_builds=10000, promise_percent=99.0
    )
    budget.burn("worker-death", 30)
    gate = ShipGate()
    gate.report(
        "audits",
        broken == 0,
        f"{len(findings)} audits, {broken} broken",
    )
    gate.report(
        "errorbudget", True, f"{100 - budget.remaining()} of 100 spent"
    )
    gate.report("cleanroom", True, "trust renewed")
    go = gate.decide()
    frozen_gate = ShipGate()
    frozen_gate.report(
        "audits", broken == 0, f"{len(findings)} audits"
    )
    frozen_gate.report(
        "errorbudget", False, "FROZEN, overspent by 10"
    )
    frozen_gate.report("cleanroom", True, "trust renewed")
    nogo = frozen_gate.decide()
    numbers = {
        "registry_audits": len(findings),
        "broken": broken,
        "go_given": go.startswith("GO"),
        "nogo_names_the_blocker": (
            "errorbudget: FROZEN, overspent by 10" in nogo
        ),
    }
    holds = (
        numbers["registry_audits"] >= 20
        and numbers["broken"] == 0
        and numbers["go_given"]
        and numbers["nogo_names_the_blocker"]
    )
    return Finding(
        audit="gatecheck",
        claim=(
            "the gate reads this repository's own audit "
            "registry live, says its boring go while all of "
            "them hold, and names the frozen budget when it "
            "does not; the audit that audits the auditors"
        ),
        numbers=numbers,
        holds=holds,
    )
