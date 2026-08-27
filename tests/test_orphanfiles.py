from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.orphanfiles import OrphanCensus


def census() -> OrphanCensus:
    return OrphanCensus(
        tree_files={
            "src/main.c": 4000,
            "src/util_old.c": 9000,
            "BUILD": 300,
            "README.md": 1200,
            "LICENSE": 800,
            "tools/gen.py": 2500,
        },
        declared_reads={"src/main.c"},
        build_files={"BUILD"},
        last_reader={
            "src/util_old.c": "the parser rewrite"
        },
    )


class TestTheCensus:
    def test_orphans_are_what_nothing_speaks_for(self):
        assert census().orphans() == [
            "src/util_old.c",
            "tools/gen.py",
        ]

    def test_docs_and_licenses_serve_humans(self):
        found = census().orphans()
        assert "README.md" not in found
        assert "LICENSE" not in found

    def test_an_empty_tree_is_refused(self):
        with pytest.raises(Invalid):
            OrphanCensus(
                tree_files={},
                declared_reads=set(),
                build_files=set(),
            ).orphans()


class TestTheReport:
    def test_the_actionable_sentence_names_the_history(self):
        report = census().report()
        assert report.startswith(
            "2 orphan(s) holding 11500 byte(s) of ambiguity"
        )
        assert (
            "src/util_old.c (9000 bytes): unread since the "
            "parser rewrite"
        ) in report
        assert (
            "tools/gen.py (2500 bytes): no reader in living "
            "memory"
        ) in report
        assert "keeping it ambient" in report

    def test_a_spoken_for_tree_says_so(self):
        chosen = census()
        chosen.declared_reads.update(
            {"src/util_old.c", "tools/gen.py"}
        )
        assert chosen.report().startswith(
            "every file is read by a target"
        )
