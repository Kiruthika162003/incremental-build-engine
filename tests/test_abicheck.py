from __future__ import annotations

import pytest

from forge.abicheck import AbiChecker
from forge.errors import Invalid

V1 = {"parse", "dump", "legacy_helper"}


def checker() -> AbiChecker:
    built = AbiChecker()
    built.dependent_imports("billing", {"parse"})
    built.dependent_imports("search", {"parse", "dump"})
    return built


class TestTheDiff:
    def test_added_symbols_are_free(self):
        added, paid, free = checker().diff(V1, V1 | {"stream"})
        assert added == ["stream"]
        assert paid == []
        assert free == []

    def test_a_paid_removal_names_its_victims(self):
        _, paid, _ = checker().diff(V1, V1 - {"parse"})
        assert paid == ["parse: breaks billing, search"]

    def test_dead_export_removal_is_hygiene(self):
        _, paid, free = checker().diff(V1, V1 - {"legacy_helper"})
        assert paid == []
        assert free == [
            "legacy_helper: nobody imports it; hygiene, not breakage"
        ]

    def test_double_declaration_is_refused(self):
        built = checker()
        with pytest.raises(Invalid):
            built.dependent_imports("billing", {"dump"})


class TestVerdicts:
    def test_one_paid_removal_makes_the_release_major(self):
        verdict = checker().release_verdict(V1, V1 - {"dump"})
        assert verdict.startswith("MAJOR: 1 removal(s)")
        assert "dump: breaks search" in verdict

    def test_additions_make_a_minor(self):
        verdict = checker().release_verdict(
            V1, (V1 | {"stream"}) - {"legacy_helper"}
        )
        assert verdict == (
            "minor: 1 symbols added, 1 dead exports cleaned"
        )

    def test_cleanup_alone_is_a_patch(self):
        verdict = checker().release_verdict(
            V1, V1 - {"legacy_helper"}
        )
        assert verdict == "patch: 1 dead exports cleaned"

    def test_an_unchanged_surface_is_a_patch(self):
        assert checker().release_verdict(V1, set(V1)) == (
            "patch: the surface is unchanged"
        )
