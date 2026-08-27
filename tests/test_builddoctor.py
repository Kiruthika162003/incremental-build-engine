from __future__ import annotations

from forge.builddoctor import Clinic, diagnose


class TestDiagnosis:
    def test_a_matching_declaration_is_healthy(self):
        prescription = diagnose(
            "auth/api",
            declared={"json", "log"},
            scanned={"json", "log"},
            observed={"json", "log"},
        )
        assert prescription.healthy()
        assert "matches reality" in prescription.page()

    def test_the_missing_need_is_added_with_its_testimony(self):
        prescription = diagnose(
            "auth/api",
            declared={"json"},
            scanned={"json", "crypto"},
            observed={"json", "crypto"},
        )
        assert prescription.add == [
            ("crypto", "observed at run time")
        ]

    def test_the_orphaned_need_is_dropped(self):
        prescription = diagnose(
            "auth/api",
            declared={"json", "oldlib"},
            scanned={"json"},
            observed={"json"},
        )
        assert prescription.drop == [
            ("oldlib", "neither scanned nor observed")
        ]

    def test_observation_outranks_the_scanner(self):
        prescription = diagnose(
            "auth/api",
            declared={"json", "debugonly"},
            scanned={"json", "debugonly"},
            observed={"json"},
        )
        assert prescription.drop[0][0] == "debugonly"
        assert "disabled branch" in prescription.drop[0][1]

    def test_without_observation_the_scan_is_the_truth(self):
        prescription = diagnose(
            "auth/api",
            declared={"json"},
            scanned={"json", "crypto"},
            observed=None,
        )
        assert prescription.add == [
            ("crypto", "scanned from the source")
        ]

    def test_the_page_reads_as_exact_edits(self):
        prescription = diagnose(
            "auth/api",
            declared={"oldlib"},
            scanned={"json"},
            observed={"json"},
        )
        page = prescription.page()
        assert "add needs = json" in page
        assert "drop needs = oldlib" in page


class TestTheClinic:
    def test_healthy_visits_are_not_counted(self):
        clinic = Clinic()
        clinic.file_visit(
            diagnose("a/x", {"j"}, {"j"}, {"j"})
        )
        assert clinic.report() == (
            "no prescriptions; the declarations hold"
        )

    def test_the_repeat_customer_is_named_a_process(self):
        clinic = Clinic()
        for number in range(3):
            clinic.file_visit(
                diagnose(
                    f"auth/t{number}",
                    declared=set(),
                    scanned={"json"},
                    observed={"json"},
                )
            )
        report = clinic.report()
        assert "auth: 3 prescriptions" in report
        assert "a rot process, not a rot incident" in report
