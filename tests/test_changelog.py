from __future__ import annotations

import pytest

from forge.changelog import ReleaseSnapshot, generate
from forge.errors import Invalid


def v1() -> ReleaseSnapshot:
    return ReleaseSnapshot(
        version="v1",
        tree={"bin/app": b"app-1", "doc/notes": b"hello"},
        source_digests={"main.c": "aa", "lib.c": "bb"},
    )


def v2() -> ReleaseSnapshot:
    return ReleaseSnapshot(
        version="v2",
        tree={"bin/app": b"app-2", "doc/notes": b"hello"},
        source_digests={"main.c": "aa", "lib.c": "cc"},
    )


class TestGeneration:
    def test_the_change_traces_to_its_source_edits(self):
        page = generate(v1(), v2())
        assert "changed: bin/app" in page
        assert "driven by 1 source edits: lib.c" in page

    def test_a_retag_says_so(self):
        retag = ReleaseSnapshot(
            version="v1.0.1",
            tree=dict(v1().tree),
            source_digests=dict(v1().source_digests),
        )
        page = generate(v1(), retag)
        assert "this is a re-tag" in page

    def test_arrivals_and_departures_are_inventory(self):
        after = ReleaseSnapshot(
            version="v2",
            tree={
                "bin/app": b"app-1",
                "bin/helper": b"fresh",
            },
            source_digests=dict(v1().source_digests),
        )
        page = generate(v1(), after)
        assert "new: bin/helper" in page
        assert "gone: doc/notes" in page

    def test_the_untraceable_change_is_a_warning_not_a_secret(self):
        after = ReleaseSnapshot(
            version="v2",
            tree={"bin/app": b"app-2", "doc/notes": b"hello"},
            source_digests=dict(v1().source_digests),
        )
        page = generate(v1(), after)
        assert "WARNING" in page
        assert "undeclared input moved" in page

    def test_one_version_twice_is_refused(self):
        with pytest.raises(Invalid, match="no changelog between"):
            generate(v1(), v1())
