from __future__ import annotations

import pytest

from forge.errors import Invalid, Missing
from forge.pathlayout import BuildConfig, PathLayout, paths_disjoint

DEBUG = BuildConfig(platform="x86", flags="-g", toolchain="gcc-12")
RELEASE = BuildConfig(platform="x86", flags="-O2", toolchain="gcc-12")


class TestDerivation:
    def test_distinct_configs_cannot_share_a_path(self):
        layout = PathLayout()
        assert paths_disjoint(layout, DEBUG, RELEASE, "app")

    def test_identical_configs_always_share(self):
        layout = PathLayout()
        twin = BuildConfig(
            platform="x86", flags="-g", toolchain="gcc-12"
        )
        assert layout.derive(DEBUG, "app") == layout.derive(
            twin, "app"
        )

    def test_the_toolchain_is_part_of_the_address(self):
        layout = PathLayout()
        upgraded = BuildConfig(
            platform="x86", flags="-g", toolchain="gcc-13"
        )
        assert layout.derive(DEBUG, "app") != layout.derive(
            upgraded, "app"
        )

    def test_nameless_targets_are_refused(self):
        with pytest.raises(Invalid):
            PathLayout().derive(DEBUG, "")


class TestTheLegend:
    def test_any_path_can_be_read_back(self):
        layout = PathLayout()
        path = layout.derive(DEBUG, "app")
        assert layout.explain(path) == (
            f"{path}: x86, -g, gcc-12"
        )

    def test_a_strangers_tree_is_named_as_such(self):
        layout = PathLayout()
        with pytest.raises(Missing, match="someone else's layout"):
            layout.explain("out/deadbeef/app")

    def test_shapeless_paths_are_refused(self):
        with pytest.raises(Invalid):
            PathLayout().explain("dist/app")

    def test_the_legend_page_lists_every_config(self):
        layout = PathLayout()
        layout.derive(DEBUG, "app")
        layout.derive(RELEASE, "app")
        page = layout.legend_page()
        assert "x86 -g gcc-12" in page
        assert "x86 -O2 gcc-12" in page
        assert PathLayout().legend_page() == "no derived paths yet"
