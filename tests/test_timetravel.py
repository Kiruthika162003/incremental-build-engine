from __future__ import annotations

import pytest

from forge.buildseal import seal_build
from forge.errors import Invalid, Missing
from forge.timetravel import BuildArchive

TOOLS = {"cc": "gcc-13.1"}
SHAPES = {"app": ()}


def archive() -> BuildArchive:
    built = BuildArchive()
    built.record(
        "rel-88", seal_build("tree-x", TOOLS, SHAPES), day=100
    )
    return built


class TestTravel:
    def test_a_complete_world_reproduces_exactly(self):
        verdict = archive().travel_to("rel-88", today=130)
        assert verdict == (
            "rel-88 reproduced exactly, 30 day(s) back, "
            "fingerprint verified"
        )

    def test_the_missing_part_is_named_as_a_purchase_order(self):
        built = archive()
        seal, _ = built.seals["rel-88"]
        built.forget_tools(seal.tool_digest)
        verdict = built.travel_to("rel-88", today=130)
        assert verdict.startswith(
            "cannot reassemble rel-88: the toolchain of day "
            "100 are gone"
        )
        assert "the tree and the graph survive" in verdict
        assert "a purchase order" in verdict

    def test_an_unarchived_build_is_missing(self):
        with pytest.raises(Missing):
            archive().travel_to("ghost", today=1)

    def test_double_archiving_is_refused(self):
        built = archive()
        with pytest.raises(Invalid):
            built.record(
                "rel-88",
                seal_build("tree-y", TOOLS, SHAPES),
                day=101,
            )


class TestTheRent:
    def test_an_untravelled_archive_is_a_museum(self):
        assert archive().rent_verdict() == (
            "1 build(s) archived, zero travels: rent paid on "
            "a museum"
        )

    def test_travels_earn_the_rent(self):
        built = archive()
        built.travel_to("rel-88", today=130)
        assert "the archive earns its rent" in built.rent_verdict()
