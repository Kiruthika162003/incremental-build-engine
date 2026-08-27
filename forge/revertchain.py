"""Revert chains: the second revert is a fork in the road, marked.

The first revert is hygiene, the fastest way to green, and
nobody should hesitate over it. The revert of a revert is a
different object wearing the same verb: it means the original
change is coming back without new information, and the third
link, reverting that, means two theories of the codebase are
taking turns being deployed, which is a fight conducted
through the version control system. The tracker follows
revert lineage by target, counts the chain, and escalates its
advice at each link: link one passes silently, link two
recommends rolling forward with a fix and names both authors
so they find each other before the tooling has to, and link
three refuses the mechanical path outright, not because the
tool can stop anyone but because a refusal in the log is the
paper trail the postmortem will want.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class RevertTracker:
    chains: dict[str, list[str]] = field(default_factory=dict)

    def record_revert(
        self, target_commit: str, author: str, subject: str
    ) -> str:
        chain = self.chains.setdefault(subject, [])
        chain.append(f"{target_commit} by {author}")
        link = len(chain)
        if link == 1:
            return (
                f"revert of {target_commit}: hygiene, the "
                "fastest way to green"
            )
        if link == 2:
            first = chain[0].split(" by ")[1]
            return (
                f"revert of a revert on {subject}: the "
                "original is coming back without new "
                f"information; {first} and {author} should "
                "find each other before the tooling has to, "
                "and rolling forward with a fix beats taking "
                "turns"
            )
        raise Invalid(
            f"link {link} on {subject}: two theories of the "
            "codebase are taking turns being deployed; this "
            "refusal is the paper trail the postmortem will "
            "want"
        )

    def open_disputes(self) -> list[str]:
        return sorted(
            f"{subject}: {len(chain)} link(s)"
            for subject, chain in self.chains.items()
            if len(chain) >= 2
        )
