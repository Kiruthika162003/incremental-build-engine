"""Engine version skew: the farm must speak one protocol or say so.

The subtlest farm corruption is not a crashed worker but a polite
one running last month's engine: it accepts the action, drops the
protocol fields it never learned, and returns a result that is
almost right. The pin makes skew a startup error instead of a
runtime mystery: the repo pins an engine version, the coordinator
enforces it on itself first, and every worker checking in is
graded against the pin's compatibility rule, same major and no
older minor, because new minors add fields that old workers would
silently drop. The roll call is the operational view: compliant
workers counted, skewed ones named with their versions and the
verdict each earned, and a farm where every worker is skewed
points the finger where it belongs, at the pin nobody rolled
forward, not at ninety healthy machines.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid

Version = tuple[int, int, int]


def parse_version(text: str) -> Version:
    parts = text.split(".")
    if len(parts) != 3 or not all(
        part.isdigit() for part in parts
    ):
        raise Invalid(
            f"{text!r} is not a version of the form major.minor.patch"
        )
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def grade(pin: Version, offered: Version) -> str:
    if offered[0] != pin[0]:
        return (
            f"refused: major {offered[0]} against pin major "
            f"{pin[0]}; the protocols are strangers"
        )
    if offered[1] < pin[1]:
        return (
            f"refused: minor {offered[1]} predates pin minor "
            f"{pin[1]} and would silently drop fields it never "
            "learned"
        )
    return "compliant"


@dataclass
class FarmRollCall:
    pin: Version
    workers: dict[str, Version] = field(default_factory=dict)

    def check_in(self, worker: str, version_text: str) -> str:
        version = parse_version(version_text)
        self.workers[worker] = version
        verdict = grade(self.pin, version)
        if verdict != "compliant":
            return f"{worker} {verdict}"
        return f"{worker} joins the farm"

    def roll_call(self) -> str:
        if not self.workers:
            raise Invalid("nobody has checked in")
        skewed = {
            worker: version
            for worker, version in self.workers.items()
            if grade(self.pin, version) != "compliant"
        }
        compliant = len(self.workers) - len(skewed)
        pin_text = ".".join(str(part) for part in self.pin)
        if not skewed:
            return (
                f"{compliant} worker(s) compliant with pin "
                f"{pin_text}; the farm speaks one protocol"
            )
        lines = [
            f"{compliant} compliant, {len(skewed)} skewed against "
            f"pin {pin_text}"
        ]
        for worker in sorted(skewed):
            version = skewed[worker]
            dotted = ".".join(str(part) for part in version)
            lines.append(
                f"  {worker} at {dotted}: "
                f"{grade(self.pin, version)}"
            )
        if len(skewed) == len(self.workers):
            lines.append(
                "  every worker is skewed: the finger points at "
                "the pin nobody rolled forward, not at "
                f"{len(skewed)} healthy machine(s)"
            )
        return "\n".join(lines)
