from __future__ import annotations

import pytest

from forge.busfactor import EditCensus
from forge.errors import Invalid


def census() -> EditCensus:
    built = EditCensus()
    built.record("auth", "asha", 45)
    built.record("auth", "ben", 3)
    built.record("auth", "chen", 2)
    built.record("billing", "asha", 20)
    built.record("billing", "ben", 18)
    built.record("billing", "chen", 12)
    built.record("attic", "dora", 2)
    return built


class TestTheFactor:
    def test_the_concentrated_package_is_a_one(self):
        assert census().bus_factor("auth") == 1

    def test_the_shared_package_needs_more_people(self):
        assert census().bus_factor("billing") == 3

    def test_an_unedited_package_cannot_be_scored(self):
        with pytest.raises(Invalid):
            census().bus_factor("ghost")

    def test_zero_edits_are_not_edits(self):
        with pytest.raises(Invalid):
            EditCensus().record("p", "a", 0)


class TestTheReport:
    def test_the_factor_of_one_gets_the_resignation_line(self):
        report = census().report("auth")
        assert report.startswith(
            "auth: bus factor 1 over 50 edit(s); asha holds 90%"
        )
        assert "one resignation letter" in report
        assert (
            "the next two features here belong to someone new"
        ) in report

    def test_the_healthy_package_still_gets_the_prescription(self):
        report = census().report("billing")
        assert report.startswith("billing: bus factor 3")
        assert "someone new" in report
        assert "resignation" not in report

    def test_dormancy_is_not_danger(self):
        report = census().report("attic")
        assert "dormancy, not danger" in report

    def test_the_two_that_behaves_like_a_one_is_named(self):
        built = EditCensus()
        built.record("infra", "lead", 82)
        built.record("infra", "helper", 18)
        report = built.report("infra")
        assert "bus factor 2" in report
        assert "behaves like a one" in report
