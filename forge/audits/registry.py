"""Every audit, one call, one page."""

from __future__ import annotations

import importlib

from forge.audits.finding import Finding

AUDITS = (
    "forge.audits.cutoffworth",
    "forge.audits.sharedmorning",
    "forge.audits.stampquarantine",
    "forge.audits.selectrefund",
    "forge.audits.workercurve",
    "forge.audits.regretledger",
)


def all_findings() -> list[Finding]:
    findings = []
    for dotted in AUDITS:
        module = importlib.import_module(dotted)
        findings.append(module.run())
    return findings


def broken() -> list[str]:
    return [
        finding.audit for finding in all_findings() if not finding.holds
    ]


def report() -> str:
    findings = all_findings()
    lines = [finding.line() for finding in findings]
    failing = sum(1 for finding in findings if not finding.holds)
    lines.append("")
    lines.append(f"{len(findings)} audits, {failing} broken")
    return "\n".join(lines)
