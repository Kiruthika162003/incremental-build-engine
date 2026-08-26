from __future__ import annotations

import pytest

from forge.errors import Invalid, Missing
from forge.workspace import Workspace


def seeded() -> Workspace:
    tree = Workspace()
    tree.write_text("src/main.c", "int main() { return 0; }")
    tree.write_text("src/lib.c", "int lib() { return 1; }")
    tree.write_text("docs/readme.txt", "hello")
    return tree


class TestFiles:
    def test_write_then_read_round_trips(self):
        tree = seeded()
        assert tree.read_text("src/main.c") == "int main() { return 0; }"

    def test_reads_and_writes_are_counted(self):
        tree = seeded()
        tree.read("src/main.c")
        tree.read("src/main.c")
        assert tree.touch_counts("src/main.c") == (2, 1)

    def test_rewrites_bump_the_generation(self):
        tree = seeded()
        tree.write_text("src/main.c", "changed")
        assert tree.files["src/main.c"].generation == 2

    def test_the_digest_peek_is_not_a_read(self):
        tree = seeded()
        tree.digest_of("src/main.c")
        assert tree.touch_counts("src/main.c") == (0, 1)

    def test_missing_files_are_named(self):
        with pytest.raises(Missing):
            seeded().read("src/ghost.c")

    def test_directory_shaped_paths_are_refused(self):
        with pytest.raises(Invalid):
            Workspace().write("src/", b"x")

    def test_delete_removes_the_record(self):
        tree = seeded()
        tree.delete("docs/readme.txt")
        assert not tree.exists("docs/readme.txt")


class TestTrees:
    def test_under_lists_a_subtree_sorted(self):
        assert seeded().under("src") == ["src/lib.c", "src/main.c"]

    def test_the_tree_digest_sees_content_changes(self):
        tree = seeded()
        before = tree.tree_digest("src")
        tree.write_text("src/lib.c", "int lib() { return 2; }")
        assert tree.tree_digest("src") != before

    def test_the_tree_digest_ignores_other_subtrees(self):
        tree = seeded()
        before = tree.tree_digest("src")
        tree.write_text("docs/readme.txt", "changed")
        assert tree.tree_digest("src") == before

    def test_a_rename_changes_the_tree(self):
        tree = seeded()
        before = tree.tree_digest("src")
        payload = tree.read("src/lib.c")
        tree.delete("src/lib.c")
        tree.write("src/lib2.c", payload)
        assert tree.tree_digest("src") != before

    def test_the_audit_line_totals_the_touches(self):
        tree = seeded()
        tree.read("src/main.c")
        assert tree.audit_line() == "3 files, 1 reads, 3 writes"
