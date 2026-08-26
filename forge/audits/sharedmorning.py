"""The remote cache turns the second machine's morning into a download.

Ten compile steps at 8 ticks each plus a 4-tick link: the first
machine builds all eleven and uploads the ten that clear the
threshold. The second machine, cold, checks out the same tree and
pays zero rule executions on the expensive steps: ten remote hits
bank 80 ticks and only the cheap link, deliberately kept under the
upload threshold, rebuilds locally. The traffic meter prices the
morning: eleven round trips and a symmetric byte flow, since what
one machine uploaded is exactly what the other downloaded, and the
receipt's shape is the argument for the threshold: the 4-tick link
was cheaper to rebuild than to fetch, so keeping it off the wire
was the right call on both machines.
"""

from __future__ import annotations

from forge.actions import Action
from forge.audits.finding import Finding
from forge.remotecache import RemoteBuilder, RemoteStore
from forge.workspace import Workspace

COMPILES = 10
COMPILE_COST = 8
LINK_COST = 4
THRESHOLD = 5


def _compile(index: int) -> Action:
    def rule(tree) -> None:
        tree.write_text(
            f"unit{index}.o",
            f"obj({tree.read_text(f'unit{index}.c')})",
        )

    return Action(
        name=f"compile unit{index}",
        command="cc -O2",
        reads=(f"unit{index}.c",),
        writes=(f"unit{index}.o",),
        rule=rule,
    )


def _link() -> Action:
    objects = tuple(f"unit{index}.o" for index in range(COMPILES))

    def rule(tree) -> None:
        parts = "+".join(tree.read_text(obj) for obj in objects)
        tree.write_text("app", f"bin[{parts}]")

    return Action(
        name="link app",
        command="ld",
        reads=objects,
        writes=("app",),
        rule=rule,
    )


def _checkout() -> Workspace:
    tree = Workspace()
    for index in range(COMPILES):
        tree.write_text(f"unit{index}.c", f"int unit{index};")
    return tree


def _morning(builder: RemoteBuilder) -> None:
    tree = _checkout()
    for index in range(COMPILES):
        builder.run(_compile(index), tree, cost=COMPILE_COST)
    builder.run(_link(), tree, cost=LINK_COST)


def run() -> Finding:
    remote = RemoteStore()
    first = RemoteBuilder(remote=remote, upload_threshold=THRESHOLD)
    second = RemoteBuilder(remote=remote, upload_threshold=THRESHOLD)
    _morning(first)
    _morning(second)
    numbers = {
        "first_machine_built": first.built,
        "second_machine_remote_hits": second.remote_hits,
        "second_machine_built": second.built,
        "second_machine_ticks_saved": second.ticks_saved,
        "round_trips": remote.round_trips,
        "bytes_symmetric": remote.bytes_downloaded == remote.bytes_uploaded,
    }
    holds = (
        first.built == COMPILES + 1
        and second.remote_hits == COMPILES
        and second.built == 1
        and second.ticks_saved == COMPILES * COMPILE_COST
        and remote.round_trips == 2 * COMPILES
        and numbers["bytes_symmetric"]
    )
    return Finding(
        audit="sharedmorning",
        claim=(
            "the second machine's morning is ten downloads and one "
            "cheap local link: 80 ticks banked, the 4-tick link "
            "rightly kept off the wire"
        ),
        numbers=numbers,
        holds=holds,
    )
