from __future__ import annotations

import pytest

from forge.errors import Invalid, Missing
from forge.sbom import BillOfMaterials, BomEntry


def bill() -> BillOfMaterials:
    built = BillOfMaterials()
    built.add(
        BomEntry(
            component="app",
            version="2.1.0",
            digest="aa" * 8,
            license_name="proprietary",
            origin="first-party",
        )
    )
    built.add(
        BomEntry(
            component="zlib",
            version="1.3",
            digest="bb" * 8,
            license_name="Zlib",
            origin="external",
        )
    )
    return built


class TestTheBill:
    def test_the_export_is_stamped_and_sorted(self):
        page = bill().export({"app", "zlib"})
        lines = page.splitlines()
        assert lines[0].startswith("sbom ")
        assert lines[1].startswith("app 2.1.0 [proprietary]")
        assert lines[2].startswith("zlib 1.3 [Zlib] (external)")

    def test_two_identical_bills_share_a_stamp(self):
        first = bill().export({"app", "zlib"})
        second = bill().export({"app", "zlib"})
        assert first == second

    def test_a_missing_line_fails_the_export_by_name(self):
        with pytest.raises(Missing, match="different document"):
            bill().export({"app", "zlib", "openssl"})

    def test_unknown_origins_are_refused(self):
        with pytest.raises(Invalid):
            BillOfMaterials().add(
                BomEntry(
                    component="x",
                    version="1",
                    digest="cc",
                    license_name="MIT",
                    origin="found-on-a-forum",
                )
            )

    def test_double_billing_is_refused(self):
        built = bill()
        with pytest.raises(Invalid):
            built.add(
                BomEntry(
                    component="zlib",
                    version="1.4",
                    digest="dd",
                    license_name="Zlib",
                    origin="external",
                )
            )


class TestSummaries:
    def test_externals_are_listable_for_the_questionnaire(self):
        assert bill().externals() == ["zlib"]

    def test_the_license_summary_counts_by_terms(self):
        assert bill().license_summary() == (
            "Zlib: 1, proprietary: 1"
        )
