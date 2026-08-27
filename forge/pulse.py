"""The pulse page: the farm is not binary, and the page admits it.

Status pages fail in one direction, optimism: the coordinator
answers, the light is green, and the developers whose uploads
are timing out learn that the dashboard is a decoration. The
pulse rates each component honestly, up, degraded with the
symptom named, or down, and computes the overall state from
the worst component on a user-visible path rather than from
an average, because averaging a down store against five green
services produces a yellow that describes nobody's morning.
The page's sharpest check is aimed at itself: when every
component reads up while the error budget is actively
burning, the pulse reports the contradiction, green dashboard
and degraded reality, and sides with reality, since the
budget meters what users experienced and the components
report what they believe about themselves.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

STATES = ("up", "degraded", "down")
USER_VISIBLE = ("coordinator", "cache", "store")


@dataclass
class PulsePage:
    components: dict[str, tuple[str, str]] = field(
        default_factory=dict
    )

    def rate(
        self, component: str, state: str, symptom: str = ""
    ) -> None:
        if state not in STATES:
            raise Invalid(f"unknown state {state}")
        if state == "degraded" and not symptom.strip():
            raise Invalid(
                f"{component}: degraded without the symptom "
                "named is a yellow light, and yellow lights "
                "are how dashboards become decorations"
            )
        self.components[component] = (state, symptom)

    def overall(self) -> str:
        missing = [
            name
            for name in USER_VISIBLE
            if name not in self.components
        ]
        if missing:
            raise Invalid(
                f"{', '.join(missing)} unrated; a pulse with "
                "missing organs is a guess"
            )
        worst = "up"
        culprit = ""
        for name in USER_VISIBLE:
            state, symptom = self.components[name]
            if STATES.index(state) > STATES.index(worst):
                worst = state
                culprit = f"{name}" + (
                    f" ({symptom})" if symptom else ""
                )
        if worst == "up":
            return "all user-visible paths up"
        return (
            f"{worst}: {culprit}; the worst component on a "
            "user-visible path, never the average, because an "
            "average describes nobody's morning"
        )

    def reality_check(self, budget_burning: bool) -> str:
        state = self.overall()
        if state.startswith("all") and budget_burning:
            return (
                "CONTRADICTION: green dashboard, degraded "
                "reality; the budget meters what users "
                "experienced and the components report what "
                "they believe about themselves, and the pulse "
                "sides with reality"
            )
        return "the page and the meters agree"
