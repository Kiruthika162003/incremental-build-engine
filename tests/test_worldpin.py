from __future__ import annotations

import pytest

from forge.errors import Invalid, Stale
from forge.worldpin import PinnedWorld

FILES = {"core.c": "int core_v100;", "app.c": "int app_v100;"}


def world() -> PinnedWorld:
    return PinnedWorld(revision=100, files=dict(FILES))


class TestThePin:
    def test_reads_answer_as_of_the_pin(self):
        pinned = world()
        pinned.commit_arrives(103, "core.c", "int core_v103;")
        assert pinned.read("core.c") == "int core_v100;"

    def test_arrivals_land_in_the_repo_not_the_view(self):
        verdict = world().commit_arrives(
            103, "core.c", "new"
        )
        assert "not in the running build's view" in verdict

    def test_a_rewound_arrival_is_refused(self):
        with pytest.raises(Invalid):
            world().commit_arrives(99, "core.c", "old")

    def test_a_file_missing_at_the_pin_is_named_with_it(self):
        with pytest.raises(Invalid) as caught:
            world().read("brand_new.c")
        assert "does not exist at revision 100" in str(
            caught.value
        )


class TestTheTornWorldDetector:
    def test_a_faithful_build_passes_the_audit(self):
        pinned = world()
        verdict = pinned.audit_consumed(
            {"core.c": "int core_v100;"}
        )
        assert "the world held" in verdict

    def test_the_torn_world_names_file_and_revisions(self):
        pinned = world()
        pinned.commit_arrives(103, "core.c", "int core_v103;")
        with pytest.raises(Stale) as caught:
            pinned.audit_consumed(
                {
                    "core.c": "int core_v103;",
                    "app.c": "int app_v100;",
                }
            )
        message = str(caught.value)
        assert message.startswith("TORN WORLD: core.c")
        assert "pinned r100, consumed r103" in message
        assert "no revision can reproduce it" in message

    def test_an_unknown_leak_is_still_torn(self):
        pinned = world()
        with pytest.raises(Stale) as caught:
            pinned.audit_consumed({"core.c": "handmade edit"})
        assert "consumed no known revision" in str(caught.value)


class TestFinishing:
    def test_a_quiet_build_finishes_quietly(self):
        assert world().finish() == (
            "built at r100; nothing moved underneath"
        )

    def test_the_moved_world_is_announced_to_the_next_build(self):
        pinned = world()
        pinned.commit_arrives(101, "a", "x")
        pinned.commit_arrives(105, "b", "y")
        verdict = pinned.finish()
        assert "2 commit(s) landed, repo now at r105" in verdict
        assert "starts from a moved world" in verdict
