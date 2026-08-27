from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.graph import Graph
from forge.vcsdelta import DeltaMapper


def mapper() -> DeltaMapper:
    graph = Graph()
    for name in ("auth.o", "auth_test", "billing.o"):
        graph.declare(name)
    built = DeltaMapper(graph=graph)
    built.declare_package(
        "auth/BUILD", ("auth.o", "auth_test")
    )
    built.declare_readers("auth/session.c", ("auth.o",))
    built.declare_readers("billing/charge.c", ("billing.o",))
    return built


class TestMapping:
    def test_a_source_maps_to_its_readers(self):
        seeds, reason = mapper().map_change("auth/session.c")
        assert seeds == ("auth.o",)
        assert reason == "source read by these targets"

    def test_a_build_file_maps_to_its_whole_package(self):
        seeds, reason = mapper().map_change("auth/BUILD")
        assert seeds == ("auth.o", "auth_test")
        assert "any rule in its package" in reason

    def test_a_deletion_wants_the_loud_failure_now(self):
        seeds, reason = mapper().map_change(
            "auth/session.c", deleted=True
        )
        assert seeds == ("auth.o",)
        assert "not the next" in reason

    def test_an_orphan_path_maps_to_nothing_loudly(self):
        seeds, reason = mapper().map_change("renamed/dir/file.c")
        assert seeds == ()
        assert reason == "nothing owns this path"

    def test_double_package_declaration_is_refused(self):
        built = mapper()
        with pytest.raises(Invalid):
            built.declare_package("auth/BUILD", ("auth.o",))


class TestSeeds:
    def test_the_seed_set_unions_without_duplicates(self):
        seeds, orphaned = mapper().seeds_for(
            [
                ("auth/session.c", False),
                ("auth/BUILD", False),
                ("mystery.txt", False),
            ]
        )
        assert seeds == ["auth.o", "auth_test"]
        assert orphaned == ["mystery.txt"]

    def test_the_report_flags_orphans_before_friday(self):
        page = mapper().report(
            [("auth/session.c", False), ("mystery.txt", False)]
        )
        assert "mystery.txt -> NOTHING" in page
        assert "orphans deserve a look before Friday" in page

    def test_a_clean_delta_reports_clean(self):
        page = mapper().report([("billing/charge.c", False)])
        assert "1 seed targets, 0 orphan paths" in page
        assert "Friday" not in page
