"""Capability grants: the action gets the keys it uses, not the keys it wants.

Sandboxes fail open through generosity: the fetch rule needs
network, so network goes into the rule template, the template
gets copied, and a year later every codegen action can reach
the internet for no reason anyone remembers. The ledger holds
grants per action class, records which grants each run
actually exercised, and the audit is a subtraction: grants
held but never exercised across the whole window are named for
revocation, with the copied-template hypothesis stated when
the same unused grant appears across many classes, because
that pattern is how over-granting spreads. Escalation is the
other direction and is louder: an action exercising a
capability it does not hold is not a report line, it is a
refusal at the moment of use, since a sandbox that logs
violations instead of stopping them is a diary, not a sandbox.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

CAPABILITIES = ("network", "clock", "env", "tmpfs-exec")


@dataclass
class GrantLedger:
    held: dict[str, frozenset[str]] = field(default_factory=dict)
    exercised: dict[str, set[str]] = field(default_factory=dict)
    refusals: list[str] = field(default_factory=list)

    def grant(self, action_class: str, caps: tuple[str, ...]) -> None:
        strangers = set(caps) - set(CAPABILITIES)
        if strangers:
            raise Invalid(
                f"unknown capability(ies): "
                f"{', '.join(sorted(strangers))}"
            )
        if action_class in self.held:
            raise Invalid(
                f"{action_class} already has its grants; "
                "changing them is a review, not a re-grant"
            )
        self.held[action_class] = frozenset(caps)
        self.exercised[action_class] = set()

    def use(self, action_class: str, cap: str) -> str:
        holds = self.held.get(action_class)
        if holds is None:
            raise Invalid(f"{action_class} was never granted")
        if cap not in holds:
            refusal = (
                f"{action_class} tried {cap} without holding "
                "it: refused at the moment of use, because a "
                "sandbox that logs instead of stopping is a "
                "diary"
            )
            self.refusals.append(refusal)
            raise Invalid(refusal)
        self.exercised[action_class].add(cap)
        return f"{action_class} used {cap}"

    def revocation_audit(self) -> str:
        lines = []
        unused_by_cap: dict[str, list[str]] = {}
        for action_class in sorted(self.held):
            unused = sorted(
                self.held[action_class]
                - self.exercised[action_class]
            )
            for cap in unused:
                unused_by_cap.setdefault(cap, []).append(
                    action_class
                )
            if unused:
                lines.append(
                    f"  {action_class}: revoke "
                    f"{', '.join(unused)}"
                )
        if not lines:
            return (
                "every grant was exercised; the keys match "
                "the locks"
            )
        header = f"{len(lines)} class(es) hold unused grants"
        spread = [
            f"  {cap} is unused across "
            f"{len(classes)} class(es): the copied-template "
            "hypothesis"
            for cap, classes in sorted(unused_by_cap.items())
            if len(classes) >= 3
        ]
        return "\n".join([header, *lines, *spread])
