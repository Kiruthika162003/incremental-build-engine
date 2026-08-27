"""The repro bundle: attach this to the ticket, not a paragraph of vibes.

"Cannot reproduce" is usually a missing ingredient, not a
missing skill, and the bundle exists to make the ingredient
list mechanical: the build seal for tree, tools, and graph,
the failing action's key and command, the exact input digests
it read, and the replay coordinates from the execution log.
The builder refuses to emit a bundle with holes, a missing
seal or an action without its inputs, because a partial
bundle downgrades "cannot reproduce" from a solved problem
back to an argument. Verification is built in: a bundle can
be checked against a fresh attempt, and the check names the
first ingredient that differs, which converts the second
worst sentence in debugging, works on my machine, into the
best one, differs at ingredient three.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid, Missing

INGREDIENTS = (
    "seal_fingerprint",
    "action_key",
    "command",
    "input_digests",
    "replay_coordinates",
)


@dataclass(frozen=True)
class ReproBundle:
    facts: dict[str, str]

    def __post_init__(self) -> None:
        holes = [
            name
            for name in INGREDIENTS
            if not self.facts.get(name, "").strip()
        ]
        if holes:
            raise Invalid(
                f"the bundle has holes: {', '.join(holes)}; a "
                "partial bundle downgrades cannot-reproduce "
                "from a solved problem back to an argument"
            )

    def ticket_attachment(self) -> str:
        lines = ["repro bundle, mechanically complete:"]
        for name in INGREDIENTS:
            lines.append(f"  {name}: {self.facts[name]}")
        return "\n".join(lines)

    def check_against(
        self, attempt: dict[str, str]
    ) -> str:
        for position, name in enumerate(INGREDIENTS, 1):
            theirs = attempt.get(name)
            if theirs is None:
                raise Missing(
                    f"the attempt did not record {name}"
                )
            if theirs != self.facts[name]:
                return (
                    f"differs at ingredient {position} "
                    f"({name}): bundle has "
                    f"{self.facts[name]}, the attempt has "
                    f"{theirs}; works-on-my-machine just "
                    "became a coordinate"
                )
        return (
            "every ingredient matches; if it still does not "
            "reproduce, the bundle is missing an ingredient "
            "the format does not know yet, and that is a bug "
            "against the format"
        )
