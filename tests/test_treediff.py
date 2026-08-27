from __future__ import annotations

from forge.treediff import diff_trees

BEFORE = {
    "src/util.c": b"int util;",
    "src/main.c": b"int main;",
    "docs/readme": b"hello",
}


class TestStories:
    def test_identical_trees_are_quiet(self):
        delta = diff_trees(dict(BEFORE), dict(BEFORE))
        assert delta.quiet()
        assert delta.page() == "identical trees"

    def test_a_move_is_a_move_not_two_events(self):
        after = dict(BEFORE)
        after["lib/util.c"] = after.pop("src/util.c")
        delta = diff_trees(BEFORE, after)
        assert delta.moved == [("src/util.c", "lib/util.c")]
        assert delta.added == []
        assert delta.removed == []

    def test_a_modification_pairs_by_path(self):
        after = dict(BEFORE, **{"src/main.c": b"int main; // v2"})
        delta = diff_trees(BEFORE, after)
        assert delta.modified == ["src/main.c"]

    def test_the_truly_new_and_gone_keep_their_columns(self):
        after = dict(BEFORE)
        del after["docs/readme"]
        after["docs/changelog"] = b"fresh words"
        delta = diff_trees(BEFORE, after)
        assert delta.removed == ["docs/readme"]
        assert delta.added == ["docs/changelog"]

    def test_a_move_plus_edit_reads_as_remove_add(self):
        after = dict(BEFORE)
        del after["src/util.c"]
        after["lib/util.c"] = b"int util; // edited in flight"
        delta = diff_trees(BEFORE, after)
        assert delta.moved == []
        assert delta.removed == ["src/util.c"]
        assert delta.added == ["lib/util.c"]


class TestTheShuffle:
    def test_identical_twins_refuse_a_guessed_pairing(self):
        before = {
            "a/empty.txt": b"",
            "b/empty.txt": b"",
        }
        after = {
            "c/empty.txt": b"",
            "d/empty.txt": b"",
        }
        delta = diff_trees(before, after)
        assert delta.moved == []
        assert len(delta.shuffled) == 1
        assert "refusing to guess" in delta.page()

    def test_the_page_reads_every_story(self):
        after = dict(BEFORE)
        after["lib/util.c"] = after.pop("src/util.c")
        after["src/main.c"] = b"int main; // v2"
        page = diff_trees(BEFORE, after).page()
        assert "moved: src/util.c -> lib/util.c" in page
        assert "modified: src/main.c" in page
