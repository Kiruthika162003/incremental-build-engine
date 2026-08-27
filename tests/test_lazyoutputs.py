from __future__ import annotations

import pytest

from forge.content import ContentStore
from forge.errors import Missing, Stale
from forge.lazyoutputs import LazyTree


def remote_build() -> LazyTree:
    tree = LazyTree(store=ContentStore())
    for number in range(9):
        tree.refer(f"obj/unit{number}.o", b"x" * 100)
    tree.refer("bin/app", b"the binary itself")
    return tree


class TestLaziness:
    def test_nothing_downloads_until_something_asks(self):
        tree = remote_build()
        assert tree.bytes_fetched == 0

    def test_opening_the_binary_fetches_only_the_binary(self):
        tree = remote_build()
        payload = tree.open("bin/app")
        assert payload == b"the binary itself"
        assert tree.bytes_fetched == len(b"the binary itself")

    def test_a_second_open_is_free(self):
        tree = remote_build()
        tree.open("bin/app")
        fetched = tree.bytes_fetched
        tree.open("bin/app")
        assert tree.bytes_fetched == fetched

    def test_the_ledger_prices_the_sky(self):
        tree = remote_build()
        tree.open("bin/app")
        assert tree.ledger() == (
            "17 bytes materialised, 900 never fetched "
            "(98% of the build stayed in the sky)"
        )

    def test_the_unknown_path_is_a_plain_missing(self):
        with pytest.raises(Missing):
            remote_build().open("bin/ghost")


class TestTheTrap:
    def test_an_evicted_reference_names_its_decider(self):
        tree = remote_build()
        tree.evict("obj/unit3.o", reason="lru swept it on tuesday")
        with pytest.raises(Stale, match="lru swept it on tuesday"):
            tree.open("obj/unit3.o")

    def test_eviction_of_nothing_is_refused(self):
        with pytest.raises(Missing):
            remote_build().evict("bin/ghost", reason="x")

    def test_shared_bytes_evict_together(self):
        tree = remote_build()
        tree.evict("obj/unit0.o", reason="swept")
        with pytest.raises(Stale):
            tree.open("obj/unit1.o")
