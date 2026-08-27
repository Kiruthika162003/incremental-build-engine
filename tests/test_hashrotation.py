from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.hashrotation import RotatingCache


def era() -> RotatingCache:
    cache = RotatingCache()
    for number in range(8):
        cache.store(f"obj{number}", f"old{number}", f"new{number}")
    cache.adopt_legacy("legacy-a", "old-a")
    cache.adopt_legacy("legacy-b", "old-b")
    return cache


class TestTheDualEra:
    def test_new_entries_carry_both_keys(self):
        cache = era()
        assert cache.read("obj0", "unused") == (
            "obj0: served under the new key"
        )

    def test_legacy_entries_rehash_on_first_read(self):
        cache = era()
        verdict = cache.read("legacy-a", "new-a")
        assert "re-hashed from the bytes on first read" in verdict
        assert "inherit the collisions" in verdict
        assert cache.read("legacy-a", "x") == (
            "legacy-a: served under the new key"
        )

    def test_a_stranger_read_is_refused(self):
        with pytest.raises(Invalid):
            era().read("ghost", "x")


class TestCutover:
    def test_the_gate_holds_below_ninety_percent(self):
        cache = era()
        assert cache.attempt_cutover().startswith(
            "hold the era: 80%"
        )

    def test_reading_raises_the_share_past_the_gate(self):
        cache = era()
        cache.read("legacy-a", "new-a")
        verdict = cache.attempt_cutover()
        assert verdict.startswith("cut over at 90%")
        assert "1 old-only entrie(s) will be refused" in verdict

    def test_after_cutover_the_unvouched_are_refused(self):
        cache = era()
        cache.read("legacy-a", "new-a")
        cache.attempt_cutover()
        with pytest.raises(Invalid) as caught:
            cache.read("legacy-b", "new-b")
        assert "nobody vouched for its bytes" in str(caught.value)

    def test_an_empty_cache_has_no_share(self):
        with pytest.raises(Invalid):
            RotatingCache().new_key_share()
