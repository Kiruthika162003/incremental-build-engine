from __future__ import annotations

import pytest

from forge.depweight import WeightScale
from forge.errors import Invalid


def scale() -> WeightScale:
    return WeightScale(
        sizes={
            "app": 100,
            "proto": 4000,
            "json": 500,
            "netlib": 800,
        },
        needs={
            "app": ("proto", "json", "netlib"),
            "netlib": ("proto",),
        },
    )


class TestTheScale:
    def test_the_closure_weighs_everything_reachable(self):
        assert scale().shipped_bytes("app") == 5400

    def test_the_shared_library_reclaims_zero(self):
        assert scale().what_if_removed("app", "proto") == 0

    def test_the_sole_road_reclaims_its_whole_weight(self):
        assert scale().what_if_removed("app", "json") == 500

    def test_dropping_netlib_reclaims_netlib_alone(self):
        assert scale().what_if_removed("app", "netlib") == 800

    def test_a_stranger_edge_is_refused(self):
        with pytest.raises(Invalid):
            scale().what_if_removed("app", "ghost")


class TestTheReport:
    def test_the_widest_door_leads_and_it_is_not_proto(self):
        report = scale().diet_report("app")
        assert report.startswith("app ships 5400 byte(s)")
        lines = report.splitlines()
        assert lines[1].startswith(
            "  netlib: 4800 byte(s) (88%)"
        )
        assert lines[2].startswith(
            "  proto: 4000 byte(s) (74%)"
        )

    def test_the_honest_zero_is_the_best_moment(self):
        report = scale().diet_report("app")
        assert (
            "dropping the edge reclaims 0: other roads reach "
            "the same code, and this zero is the scale working"
        ) in report

    def test_reclaimable_edges_print_their_prize(self):
        report = scale().diet_report("app")
        assert "json: 500 byte(s) (9%)" in report
        assert "reclaims 500" in report
