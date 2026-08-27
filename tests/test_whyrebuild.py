from __future__ import annotations

import pytest

from forge.errors import Invalid, Missing
from forge.whyrebuild import ActionShot, RebuildExplainer


def shot(command, inputs, outputs):
    return ActionShot(
        command=command,
        inputs=tuple(sorted(inputs.items())),
        outputs=tuple(outputs),
    )


def two_step(core_digest_after):
    explainer = RebuildExplainer()
    explainer.record(
        {
            "compile": shot(
                "cc core.c",
                {"core.c": "d1"},
                ["libcore.o"],
            ),
            "link": shot(
                "ld libcore.o",
                {"libcore.o": "o1"},
                ["app"],
            ),
        }
    )
    explainer.record(
        {
            "compile": shot(
                "cc core.c",
                {"core.c": core_digest_after},
                ["libcore.o"],
            ),
            "link": shot(
                "ld libcore.o",
                {"libcore.o": "o2" if core_digest_after != "d1" else "o1"},
                ["app"],
            ),
        }
    )
    return explainer


class TestSingleReasons:
    def test_the_first_build_is_its_own_reason(self):
        explainer = RebuildExplainer()
        explainer.record(
            {"compile": shot("cc a.c", {"a.c": "d1"}, ["a.o"])}
        )
        explainer.record(
            {
                "compile": shot("cc a.c", {"a.c": "d1"}, ["a.o"]),
                "link": shot("ld a.o", {"a.o": "x"}, ["app"]),
            }
        )
        assert explainer.explain("link") == (
            "link ran because it had never been built"
        )

    def test_a_command_change_quotes_both_commands(self):
        explainer = RebuildExplainer()
        explainer.record(
            {"compile": shot("cc -O0 a.c", {"a.c": "d1"}, ["a.o"])}
        )
        explainer.record(
            {"compile": shot("cc -O2 a.c", {"a.c": "d1"}, ["a.o"])}
        )
        story = explainer.explain("compile")
        assert "its command changed" in story
        assert "was: cc -O0 a.c" in story
        assert "now: cc -O2 a.c" in story

    def test_gained_and_lost_inputs_are_both_named(self):
        explainer = RebuildExplainer()
        explainer.record(
            {"compile": shot("cc", {"a.c": "d1", "old.h": "h"}, ["a.o"])}
        )
        explainer.record(
            {"compile": shot("cc", {"a.c": "d1", "new.h": "h"}, ["a.o"])}
        )
        story = explainer.explain("compile")
        assert "gained inputs ['new.h']" in story
        assert "lost inputs ['old.h']" in story

    def test_an_unchanged_target_blames_the_cache_not_the_graph(self):
        explainer = two_step("d1")
        assert "cache's failure" in explainer.explain("link")


class TestTheChain:
    def test_the_chain_walks_to_the_edited_file(self):
        explainer = two_step("d2")
        story = explainer.explain("link")
        assert "link ran because libcore.o changed" in story
        assert "which compile produced" in story
        assert "core.c was edited (root cause)" in story

    def test_root_causes_extracts_just_the_files(self):
        explainer = two_step("d2")
        assert explainer.root_causes("link") == ["core.c"]

    def test_a_cycle_of_blame_does_not_loop_forever(self):
        explainer = RebuildExplainer()
        first = {
            "a": shot("mk a", {"b.out": "1"}, ["a.out"]),
            "b": shot("mk b", {"a.out": "1"}, ["b.out"]),
        }
        second = {
            "a": shot("mk a", {"b.out": "2"}, ["a.out"]),
            "b": shot("mk b", {"a.out": "2"}, ["b.out"]),
        }
        explainer.record(first)
        explainer.record(second)
        assert "already explained above" in explainer.explain("a")


class TestRefusals:
    def test_one_build_cannot_explain_anything(self):
        explainer = RebuildExplainer()
        explainer.record(
            {"compile": shot("cc", {"a.c": "d"}, ["a.o"])}
        )
        with pytest.raises(Invalid):
            explainer.explain("compile")

    def test_a_stranger_target_is_missing(self):
        explainer = two_step("d1")
        with pytest.raises(Missing):
            explainer.explain("ghost")

    def test_an_empty_build_is_refused(self):
        with pytest.raises(Invalid):
            RebuildExplainer().record({})
