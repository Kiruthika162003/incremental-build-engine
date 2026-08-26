from __future__ import annotations

import pytest

from forge.errors import Missing
from forge.srcscan import grade, scan_includes, transitive_scan
from forge.workspace import Workspace


def world() -> Workspace:
    tree = Workspace()
    tree.write_text(
        "main.c",
        'include "util.h"\ninclude "config.h"\nint main;',
    )
    tree.write_text("util.h", 'include "base.h"\n#define U 1')
    tree.write_text("base.h", "#define B 1")
    tree.write_text("config.h", "#define C 1")
    return tree


class TestScanning:
    def test_direct_includes_are_read_from_the_text(self):
        assert scan_includes(world(), "main.c") == [
            "util.h",
            "config.h",
        ]

    def test_the_transitive_scan_follows_the_chain(self):
        assert transitive_scan(world(), "main.c") == [
            "base.h",
            "config.h",
            "util.h",
        ]

    def test_missing_files_are_named(self):
        with pytest.raises(Missing):
            scan_includes(world(), "ghost.c")

    def test_a_missing_include_is_skipped_not_invented(self):
        tree = world()
        tree.write_text("main.c", 'include "nowhere.h"\nint main;')
        assert transitive_scan(tree, "main.c") == []


class TestGrading:
    def test_an_exact_scan_may_seed_the_graph(self):
        tree = world()
        result = grade(
            tree,
            "main.c",
            ["main.c", "util.h", "config.h", "base.h"],
        )
        assert result.verdict() == "exact: the scan may seed the graph"

    def test_the_disabled_branch_reads_as_waste(self):
        tree = world()
        result = grade(tree, "main.c", ["main.c", "util.h", "base.h"])
        assert result.overapproximated() == ["config.h"]
        assert result.verdict().startswith("safe but wasteful")

    def test_the_macro_assembled_include_reads_as_unsafe(self):
        tree = world()
        result = grade(
            tree,
            "main.c",
            ["main.c", "util.h", "config.h", "base.h", "secret.h"],
        )
        assert result.underapproximated() == ["secret.h"]
        assert result.verdict().startswith("UNSAFE")

    def test_unsafe_outranks_wasteful(self):
        tree = world()
        result = grade(tree, "main.c", ["main.c", "secret.h"])
        assert result.overapproximated()
        assert result.verdict().startswith("UNSAFE")
