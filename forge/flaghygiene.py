"""Flag hygiene: the flags are part of the key, so dirty flags starve the cache.

Two commands that differ only in include-path order compile the
same bytes, but a cache keyed on the raw string sees strangers,
and a farm of developers with shuffled flags shares nothing. The
normalizer canonicalizes what is provably order-free, sorts -D
and -I groups while leaving positional flags alone, so equivalent
commands collide into one key. The auditor hunts the flags that
poison keys outright: embedded absolute paths that differ per
machine, timestamp macros that differ per second, and random
seeds that differ per run, each named with its repair, because a
cache with a 3 percent hit rate is usually not a small cache but
a poisoned key, and the poison is always in the flags.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid

SORTABLE_PREFIXES = ("-D", "-I", "-W", "-f")
POISON_MACROS = ("__DATE__", "__TIME__", "BUILD_TIME", "BUILD_HOST")


@dataclass(frozen=True)
class Complaint:
    flag: str
    reason: str
    repair: str

    def line(self) -> str:
        return f"{self.flag}: {self.reason}; {self.repair}"


def normalize(command: str) -> str:
    if not command.strip():
        raise Invalid("an empty command cannot be normalized")
    words = command.split()
    head, rest = words[0], words[1:]
    sortable = sorted(
        word
        for word in rest
        if word.startswith(SORTABLE_PREFIXES)
    )
    positional = [
        word
        for word in rest
        if not word.startswith(SORTABLE_PREFIXES)
    ]
    return " ".join([head, *sortable, *positional])


def equivalent(first: str, second: str) -> bool:
    return normalize(first) == normalize(second)


def audit(command: str, machine_root: str = "/home") -> list[Complaint]:
    complaints = []
    for word in command.split():
        for macro in POISON_MACROS:
            if macro in word:
                complaints.append(
                    Complaint(
                        flag=word,
                        reason=(
                            "bakes the clock or the host into "
                            "the output"
                        ),
                        repair=(
                            "stamp late, after the cache, or "
                            "take the value from a declared input"
                        ),
                    )
                )
        if word.startswith("-I") and machine_root in word:
            complaints.append(
                Complaint(
                    flag=word,
                    reason=(
                        "carries an absolute path that differs "
                        "per machine"
                    ),
                    repair="make the include path workspace-relative",
                )
            )
        if "--seed=" in word and "--seed=0" not in word:
            complaints.append(
                Complaint(
                    flag=word,
                    reason="a per-run seed makes every key unique",
                    repair="fix the seed or hash the inputs instead",
                )
            )
    return complaints


def hygiene_report(commands: list[str]) -> str:
    if not commands:
        raise Invalid("no commands to grade")
    keys = {normalize(command) for command in commands}
    collisions = len(commands) - len(keys)
    poisoned = sum(1 for command in commands if audit(command))
    lines = [
        f"{len(commands)} command(s), {len(keys)} canonical "
        f"key(s), {collisions} recovered by normalization, "
        f"{poisoned} still poisoned"
    ]
    for command in commands:
        for complaint in audit(command):
            lines.append(f"  {complaint.line()}")
    return "\n".join(lines)
