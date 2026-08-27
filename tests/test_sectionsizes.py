from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.sectionsizes import SectionTracker

BUILD_ONE = {".text": 1000, ".data": 200, ".debug": 3000}


class TestDeltas:
    def test_the_section_names_the_suspect_with_its_share(self):
        tracker = SectionTracker()
        tracker.record(dict(BUILD_ONE))
        tracker.record(
            {".text": 1400, ".data": 300, ".debug": 3000}
        )
        report = tracker.delta_report()
        assert ".text: +400 (80% of the growth)" in report
        assert ".data: +100 (20% of the growth)" in report

    def test_the_debug_only_growth_is_a_named_false_alarm(self):
        tracker = SectionTracker()
        tracker.record(dict(BUILD_ONE))
        tracker.record(
            {".text": 1000, ".data": 200, ".debug": 9000}
        )
        report = tracker.delta_report()
        assert "do not page the performance channel" in report

    def test_a_byte_stable_binary_says_so(self):
        tracker = SectionTracker()
        tracker.record(dict(BUILD_ONE))
        tracker.record(dict(BUILD_ONE))
        assert tracker.delta_report() == (
            "no section moved; the binary is byte-stable"
        )

    def test_unknown_sections_are_carried_not_refused(self):
        tracker = SectionTracker()
        tracker.record(dict(BUILD_ONE))
        tracker.record(
            dict(BUILD_ONE, **{".llvm_addrsig": 50})
        )
        assert ".llvm_addrsig: +50" in tracker.delta_report()

    def test_one_build_has_no_delta(self):
        tracker = SectionTracker()
        tracker.record(dict(BUILD_ONE))
        with pytest.raises(Invalid):
            tracker.delta_report()

    def test_negative_sizes_are_refused(self):
        with pytest.raises(Invalid):
            SectionTracker().record({".text": -1})


class TestShippedSize:
    def test_stripped_sections_do_not_ship(self):
        tracker = SectionTracker()
        tracker.record(dict(BUILD_ONE))
        assert tracker.shipped_size() == 1200
