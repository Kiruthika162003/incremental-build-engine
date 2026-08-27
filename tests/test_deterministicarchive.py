from __future__ import annotations

import pytest

from forge.deterministicarchive import (
    nondeterminism_sources,
    reproducibility_check,
    write_deterministic,
    write_sloppy,
)
from forge.errors import Invalid

FILES = {"bin/app": "the binary", "doc/readme": "hello"}


class TestDeterminism:
    def test_the_same_tree_makes_the_same_archive(self):
        first = write_deterministic(dict(FILES))
        second = write_deterministic(dict(FILES))
        assert first.digest() == second.digest()

    def test_declaration_order_cannot_leak_in(self):
        forward = write_deterministic(
            {"a.txt": "one", "b.txt": "two"}
        )
        backward = write_deterministic(
            {"b.txt": "two", "a.txt": "one"}
        )
        assert forward.digest() == backward.digest()

    def test_content_changes_change_the_archive(self):
        first = write_deterministic(dict(FILES))
        second = write_deterministic(
            dict(FILES, **{"bin/app": "the binary v2"})
        )
        assert first.digest() != second.digest()

    def test_an_empty_archive_is_refused(self):
        with pytest.raises(Invalid):
            write_deterministic({})


class TestTheChecklist:
    def test_the_sloppy_archive_names_its_sins(self):
        sloppy = write_sloppy(
            dict(FILES),
            clock=1723456,
            user="jenkins:staff",
            listing_order=["doc/readme", "bin/app"],
        )
        sources = nondeterminism_sources(sloppy)
        assert len(sources) == 3
        assert any("directory listing" in line for line in sources)
        assert any("the clock is" in line for line in sources)
        assert any("the machine is" in line for line in sources)

    def test_the_clean_archive_has_no_sins(self):
        assert nondeterminism_sources(
            write_deterministic(dict(FILES))
        ) == []


class TestTheCheck:
    def test_two_clean_builds_verify_byte_identical(self):
        verdict = reproducibility_check(
            write_deterministic(dict(FILES)),
            write_deterministic(dict(FILES)),
        )
        assert verdict == (
            "reproducible: the archives are byte-identical"
        )

    def test_the_migration_gets_a_checklist_not_a_lecture(self):
        sloppy = write_sloppy(
            dict(FILES),
            clock=99,
            user="ci:ci",
            listing_order=["doc/readme", "bin/app"],
        )
        clean = write_deterministic(dict(FILES))
        verdict = reproducibility_check(sloppy, clean)
        assert verdict.startswith("NOT reproducible; the checklist:")
        assert "the clock is in the archive" in verdict

    def test_real_content_drift_is_not_blamed_on_the_tool(self):
        first = write_deterministic(dict(FILES))
        second = write_deterministic(
            dict(FILES, **{"bin/app": "different"})
        )
        assert reproducibility_check(first, second) == (
            "NOT reproducible: the content itself differs"
        )
