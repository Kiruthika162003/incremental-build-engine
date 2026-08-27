"""Ownership: every package answers to someone, and the roster is checked.

A change to a package routes to its owners for review, and the
two rot modes are both quiet: a package nobody owns routes
nowhere, and a package owned only by the departed routes to a
mailbox that bounces. The book maps packages to owner lists,
inherits ownership downward so deep trees stay declarable at the
top, and audits against the active roster: orphan packages and
ghost-owned packages come back as separate lists because the fix
for one is a volunteer and for the other a handover. Review
routing returns the nearest owners up the tree plus the reason
they were chosen, and the load report counts packages per owner,
since the colleague who owns ninety packages is a bus factor
wearing a compliment.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class OwnerBook:
    owners: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def declare(self, package: str, names: tuple[str, ...]) -> None:
        if not names:
            raise Invalid(
                f"{package}: an empty owner list is an orphan with "
                f"paperwork"
            )
        if package in self.owners:
            raise Invalid(f"{package} already has owners")
        self.owners[package] = names

    def route(self, package: str) -> tuple[tuple[str, ...], str]:
        cursor = package
        while True:
            if cursor in self.owners:
                reason = (
                    "owned directly"
                    if cursor == package
                    else f"inherited from {cursor}"
                )
                return self.owners[cursor], reason
            if "/" not in cursor:
                return (), "no owner anywhere up the tree"
            cursor = cursor.rsplit("/", 1)[0]

    def audit(
        self, packages: list[str], active_roster: set[str]
    ) -> tuple[list[str], list[str]]:
        orphans = []
        ghost_owned = []
        for package in sorted(packages):
            names, _ = self.route(package)
            if not names:
                orphans.append(package)
                continue
            if not any(name in active_roster for name in names):
                ghost_owned.append(package)
        return orphans, ghost_owned

    def load_report(self, packages: list[str]) -> str:
        per_owner: dict[str, int] = {}
        for package in packages:
            names, _ = self.route(package)
            for name in names:
                per_owner[name] = per_owner.get(name, 0) + 1
        if not per_owner:
            return "nobody owns anything; start with a volunteer"
        lines = [
            f"{name}: {count} packages"
            for name, count in sorted(
                per_owner.items(), key=lambda row: (-row[1], row[0])
            )
        ]
        heaviest = max(per_owner.values())
        if heaviest >= 10:
            lines.append(
                "the top of this list is a bus factor wearing a "
                "compliment"
            )
        return "\n".join(lines)
