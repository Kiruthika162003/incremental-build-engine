"""The decision chronicle: why it is like this, answerable without seances.

Every build platform carries load-bearing weirdness, the
retry count that is 4 for a reason nobody remembers, and the
chronicle is where the reasons go to survive their authors:
each decision is recorded with its context and consequences,
status accepted until another decision supersedes it by name,
and the supersede link is the whole payload, because a
decision replaced by nothing recorded is how the same debate
reruns annually with worse attendance. The lint walks the
chain: superseded decisions must point at a real successor,
accepted decisions past a review age are flagged not as wrong
but as unexamined, and the orphan check catches the classic
rot, a decision marked superseded-by pointing at a decision
that was never written, which is a promise of a reason,
broken.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

REVIEW_AGE_DAYS = 730


@dataclass
class Chronicle:
    decisions: dict[str, dict] = field(default_factory=dict)

    def record(
        self,
        key: str,
        why: str,
        decided_on_day: int,
    ) -> str:
        if key in self.decisions:
            raise Invalid(
                f"{key} exists; new thinking supersedes, it "
                "does not overwrite"
            )
        if not why.strip():
            raise Invalid(
                "a decision without its why is a fact, and "
                "facts do not survive their authors"
            )
        self.decisions[key] = {
            "why": why,
            "day": decided_on_day,
            "status": "accepted",
            "superseded_by": None,
        }
        return f"{key} recorded, accepted"

    def supersede(
        self, old_key: str, new_key: str
    ) -> str:
        if old_key not in self.decisions:
            raise Invalid(f"{old_key} was never recorded")
        if self.decisions[old_key]["status"] != "accepted":
            raise Invalid(
                f"{old_key} is already superseded; chains "
                "grow at the head"
            )
        self.decisions[old_key]["status"] = "superseded"
        self.decisions[old_key]["superseded_by"] = new_key
        return f"{old_key} superseded by {new_key}"

    def why(self, key: str) -> str:
        held = self.decisions.get(key)
        if held is None:
            raise Invalid(
                f"{key} has no recorded decision; the answer "
                "lives in somebody's memory, which is not a "
                "storage tier"
            )
        if held["status"] == "superseded":
            return (
                f"{key}: superseded by "
                f"{held['superseded_by']}; the old why was: "
                f"{held['why']}"
            )
        return f"{key}: {held['why']}"

    def lint(self, today: int) -> str:
        broken_promises = []
        unexamined = []
        for key, held in sorted(self.decisions.items()):
            successor = held["superseded_by"]
            if (
                successor is not None
                and successor not in self.decisions
            ):
                broken_promises.append(
                    f"{key} superseded by {successor}, which "
                    "was never written: a promise of a "
                    "reason, broken"
                )
            if (
                held["status"] == "accepted"
                and today - held["day"] > REVIEW_AGE_DAYS
            ):
                unexamined.append(
                    f"{key}: accepted "
                    f"{today - held['day']} day(s) ago; not "
                    "wrong, unexamined"
                )
        if not broken_promises and not unexamined:
            return "the chronicle is whole"
        return "\n".join(
            [
                f"{len(broken_promises)} broken promise(s), "
                f"{len(unexamined)} unexamined",
                *(f"  {line}" for line in broken_promises),
                *(f"  {line}" for line in unexamined),
            ]
        )
