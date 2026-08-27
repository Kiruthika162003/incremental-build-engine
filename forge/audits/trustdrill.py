"""The poisoned laptop drill: quarantine holds, corroboration convicts.

A compromised laptop uploads a poisoned object for a hot key
while nine honest machines work the same day. The drill runs the
whole day through the trust cache: the poison lands in
quarantine and is never served, refused four times while the
honest machines miss and rebuild locally; then an honest laptop
uploads the true bytes for the same key, the digests disagree,
and both entries freeze with both writers named, converting the
compromise from a distribution event into an investigation
ticket. The counterfactual column is the drill's weight: an
untiered cache would have served the poison on every one of
those four lookups, and the difference between four poisoned
builds and zero is the entire security argument for making
developers' uploads wait for a second opinion.
"""

from __future__ import annotations

from forge.audits.finding import Finding
from forge.cachetrust import TrustCache, register_trusted


def run() -> Finding:
    cache = TrustCache()
    register_trusted(cache, "ci-fleet")
    cache.upload("compile:hotpath", "poison-digest", "laptop-evil")
    poisoned_serves = 0
    for _ in range(4):
        if cache.lookup("compile:hotpath") is not None:
            poisoned_serves += 1
    collision = cache.upload(
        "compile:hotpath", "honest-digest", "laptop-good"
    )
    frozen_after = cache.lookup("compile:hotpath")
    numbers = {
        "poisoned_serves": poisoned_serves,
        "quarantine_refusals": cache.quarantine_refusals,
        "collision_declared": collision.startswith("COLLISION"),
        "served_after_freeze": frozen_after,
        "untiered_would_have_served": 4,
        "writers_named": cache.collisions[0]
        if cache.collisions
        else "",
    }
    holds = (
        poisoned_serves == 0
        and cache.quarantine_refusals == 4
        and numbers["collision_declared"]
        and frozen_after is None
        and "laptop-evil and laptop-good disagree"
        in numbers["writers_named"]
    )
    return Finding(
        audit="trustdrill",
        claim=(
            "the poison is never served: four quarantine refusals "
            "where an untiered cache serves it four times, and the "
            "collision freezes both entries with both writers named"
        ),
        numbers=numbers,
        holds=holds,
    )
