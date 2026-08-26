from __future__ import annotations

import pytest

from forge.content import (
    ContentStore,
    digest_bytes,
    digest_pairs,
    digest_text,
)
from forge.errors import Invalid, Missing


class TestDigests:
    def test_identity_is_the_bytes(self):
        assert digest_bytes(b"hello") == digest_bytes(b"hello")
        assert digest_bytes(b"hello") != digest_bytes(b"hello ")

    def test_text_is_utf8_bytes(self):
        assert digest_text("hello") == digest_bytes(b"hello")

    def test_the_digest_is_fixed_width(self):
        assert len(digest_bytes(b"")) == 32
        assert len(digest_bytes(b"x" * 100000)) == 32


class TestTreeFolds:
    def test_order_of_declaration_does_not_matter(self):
        a = digest_pairs([("lib.c", "aa"), ("main.c", "bb")])
        b = digest_pairs([("main.c", "bb"), ("lib.c", "aa")])
        assert a == b

    def test_names_are_part_of_the_tree(self):
        a = digest_pairs([("main.c", "aa")])
        b = digest_pairs([("renamed.c", "aa")])
        assert a != b

    def test_a_changed_entry_changes_the_fold(self):
        a = digest_pairs([("main.c", "aa"), ("lib.c", "bb")])
        b = digest_pairs([("main.c", "aa"), ("lib.c", "cc")])
        assert a != b

    def test_duplicate_names_are_refused(self):
        with pytest.raises(Invalid, match="ambiguous"):
            digest_pairs([("main.c", "aa"), ("main.c", "bb")])

    def test_the_boundary_cannot_be_gamed(self):
        a = digest_pairs([("ab", "cd")])
        b = digest_pairs([("a", "bcd")])
        assert a != b


class TestTheStore:
    def test_bytes_round_trip(self):
        store = ContentStore()
        key = store.put(b"object one")
        assert store.get(key) == b"object one"

    def test_identical_puts_collapse(self):
        store = ContentStore()
        first = store.put(b"same")
        second = store.put(b"same")
        assert first == second
        assert store.writes == 1
        assert store.deduplicated == 1

    def test_the_missing_are_named(self):
        with pytest.raises(Missing):
            ContentStore().get("0" * 32)

    def test_the_economy_line_reads_the_ledger(self):
        store = ContentStore()
        store.put(b"abc")
        store.put(b"abc")
        store.put(b"defg")
        assert store.economy() == (
            "2 objects stored, 1 duplicate puts collapsed, 7 bytes held"
        )
