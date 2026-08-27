"""A sprint of edits prices the incremental linker's envelope.

Ten working days against a two-object binary: seven body edits
that fit the padding, one symbol addition, one object-set change
when a file lands, and one day the intern relinks by hand and the
binary on disk stops being the linker's own child. The prose
guess of the bill was wrong twice before the ledger settled it:
seven patches at 4 ticks and four full links at 40 pay 188 where
always-full pays 440, a saving of 252, with every fallback's
reason on the ledger. The distribution is the honest part: the envelope held
for seven of ten edits, and the three exits were three different
walls, symbols, membership, and provenance, which is the audit's
answer to "can we just patch always": the walls are real and
each has its own name.
"""

from __future__ import annotations

from forge.audits.finding import Finding
from forge.incrementallink import IncrementalLinker, ObjectState

MAIN = ObjectState(symbols=("main",), size=100)
UTIL = ObjectState(symbols=("util",), size=80)


def run() -> Finding:
    linker = IncrementalLinker(reserved_padding=30)
    linker.link(
        {"main.o": MAIN, "util.o": UTIL}, binary_digest=None
    )
    for day in range(1, 8):
        edited = ObjectState(symbols=("main",), size=100 + day)
        linker.link(
            {"main.o": edited, "util.o": UTIL},
            binary_digest=linker.last_binary_digest,
        )
    resymboled = ObjectState(symbols=("main", "new_entry"), size=107)
    linker.link(
        {"main.o": resymboled, "util.o": UTIL},
        binary_digest=linker.last_binary_digest,
    )
    landed = {
        "main.o": resymboled,
        "util.o": UTIL,
        "extra.o": ObjectState(symbols=("extra",), size=10),
    }
    linker.link(landed, binary_digest=linker.last_binary_digest)
    linker.link(landed, binary_digest="the-interns-hand-relink")
    reasons = " | ".join(linker.fallback_reasons)
    numbers = {
        "patches": linker.patches,
        "full_links": linker.full_links,
        "distinct_walls": len(set(linker.fallback_reasons)),
        "ledger": linker.season_ledger(),
    }
    holds = (
        linker.patches == 7
        and linker.full_links == 4
        and len(set(linker.fallback_reasons)) == 3
        and "symbol set moved" in reasons
        and "object set changed" in reasons
        and "own child" in reasons
        and linker.season_ledger()
        == "7 patches, 4 full links; 252 ticks saved against always-full"
    )
    return Finding(
        audit="linkseason",
        claim=(
            "the envelope held for seven of ten edits and the three "
            "exits hit three different walls: symbols, membership, "
            "and provenance each have their own name"
        ),
        numbers=numbers,
        holds=holds,
    )
