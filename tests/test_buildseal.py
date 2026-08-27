from __future__ import annotations

import pytest

from forge.buildseal import compare, seal_build
from forge.errors import Invalid

TOOLS = {"cc": "gcc-13.1", "ld": "gnu-ld-2.41"}
SHAPES = {"app": ("core",), "core": ()}


def our_seal():
    return seal_build("tree-d1", dict(TOOLS), dict(SHAPES))


class TestSealing:
    def test_the_same_ingredients_seal_identically(self):
        assert (
            our_seal().fingerprint() == our_seal().fingerprint()
        )

    def test_any_part_moves_the_fingerprint(self):
        other_tree = seal_build("tree-d2", TOOLS, SHAPES)
        other_tools = seal_build(
            "tree-d1", {"cc": "gcc-13.2", "ld": "gnu-ld-2.41"}, SHAPES
        )
        other_graph = seal_build(
            "tree-d1", TOOLS, {"app": (), "core": ()}
        )
        prints = {
            our_seal().fingerprint(),
            other_tree.fingerprint(),
            other_tools.fingerprint(),
            other_graph.fingerprint(),
        }
        assert len(prints) == 4

    def test_a_toolless_build_is_refused(self):
        with pytest.raises(Invalid):
            seal_build("t", {}, SHAPES)


class TestComparison:
    def test_agreement_is_one_line(self):
        assert compare(our_seal(), our_seal()).startswith(
            "same build:"
        )

    def test_the_mismatch_names_the_part(self):
        theirs = seal_build("tree-d2", TOOLS, SHAPES)
        verdict = compare(our_seal(), theirs)
        assert verdict == (
            "same graph and toolchain, sources differ"
        )

    def test_the_toolchain_diff_names_the_tool(self):
        their_tools = {"cc": "gcc-13.2", "ld": "gnu-ld-2.41"}
        theirs = seal_build("tree-d1", their_tools, SHAPES)
        verdict = compare(
            our_seal(),
            theirs,
            our_tools=TOOLS,
            their_tools=their_tools,
        )
        assert (
            "toolchain differs (cc: gcc-13.1 against gcc-13.2)"
        ) in verdict
        assert verdict.startswith("same sources and graph")

    def test_a_missing_tool_reads_as_absent(self):
        their_tools = {"cc": "gcc-13.1"}
        theirs = seal_build("tree-d1", their_tools, SHAPES)
        verdict = compare(
            our_seal(),
            theirs,
            our_tools=TOOLS,
            their_tools=their_tools,
        )
        assert "ld: gnu-ld-2.41 against absent" in verdict
