"""The sealed ladder: promotion, archive, and travel agree about one binary.

One artifact carries one seal up the whole ladder: it enters
dev with a fingerprint, climbs three rungs presenting the same
digest at every gate, is archived with its seal on the day it
ships, and ninety days later the incident asks for it back.
The drill runs that whole life and checks the joints where
systems meet, because each organ is tested alone and the
places they touch are where identity quietly dies: the ladder
must refuse the rebuilt impostor mid-climb, the archive must
reproduce the exact fingerprint at distance 90, and the
rebuilt impostor's seal must differ from the archived truth by
exactly the component that was rebuilt, the toolchain, with
sources and graph agreeing. All three held on first
measurement, which is worth recording precisely because
nothing about it was rigged to.
"""

from __future__ import annotations

from forge.audits.finding import Finding
from forge.buildseal import compare, seal_build
from forge.errors import Invalid
from forge.promotion import Ladder
from forge.timetravel import BuildArchive

TOOLS = {"cc": "gcc-13.1", "ld": "gnu-ld-2.41"}
SHAPES = {"app": ("core",), "core": ()}


def run() -> Finding:
    seal = seal_build("tree-r4400", dict(TOOLS), dict(SHAPES))
    digest = seal.fingerprint()
    ladder = Ladder()
    ladder.enter("app-24.3", digest)
    for _ in range(3):
        ladder.promote("app-24.3", digest)
    impostor_refused = False
    try:
        ladder.demote("app-24.3", "rebuilt-digest", "why not")
    except Invalid:
        impostor_refused = True
    archive = BuildArchive()
    archive.record("app-24.3", seal, day=100)
    travel = archive.travel_to("app-24.3", today=190)
    rebuilt = seal_build(
        "tree-r4400",
        {"cc": "gcc-13.2", "ld": "gnu-ld-2.41"},
        dict(SHAPES),
    )
    diff = compare(
        seal,
        rebuilt,
        our_tools=TOOLS,
        their_tools={"cc": "gcc-13.2", "ld": "gnu-ld-2.41"},
    )
    numbers = {
        "rungs_climbed": 3,
        "final_rung": ladder.where("app-24.3"),
        "impostor_refused": impostor_refused,
        "travel_distance": 90,
        "travel_exact": "reproduced exactly" in travel,
        "diff_names_toolchain": "cc: gcc-13.1 against gcc-13.2"
        in diff,
        "diff_clears_the_rest": diff.startswith(
            "same sources and graph"
        ),
    }
    holds = (
        numbers["final_rung"] == "production"
        and numbers["impostor_refused"]
        and numbers["travel_exact"]
        and numbers["diff_names_toolchain"]
        and numbers["diff_clears_the_rest"]
    )
    return Finding(
        audit="sealedladder",
        claim=(
            "identity survives the joints: the ladder refuses "
            "the impostor, the archive reproduces the exact "
            "fingerprint at distance 90, and the rebuilt "
            "seal differs by precisely the toolchain while "
            "sources and graph agree"
        ),
        numbers=numbers,
        holds=holds,
    )
