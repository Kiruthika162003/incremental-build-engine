from __future__ import annotations

import pytest

from forge.casehazard import CaseAuditor
from forge.errors import Invalid


class TestSources:
    def test_the_readme_pair_is_named_with_both_spellings(self):
        auditor = CaseAuditor(
            source_paths=("README.md", "readme.md", "main.c"),
            output_paths=(),
        )
        report = auditor.source_report()
        assert report.startswith("1 source collision(s)")
        assert "README.md / readme.md fold into one file" in report

    def test_a_clean_tree_is_declared_portable(self):
        auditor = CaseAuditor(
            source_paths=("a.c", "b.c"), output_paths=()
        )
        assert auditor.source_report() == (
            "sources are case-clean on every filesystem"
        )


class TestOutputs:
    def test_colliding_outputs_are_refused_not_warned(self):
        auditor = CaseAuditor(
            source_paths=(),
            output_paths=("bin/App", "bin/app"),
        )
        with pytest.raises(Invalid) as caught:
            auditor.check_outputs()
        assert "bin/App / bin/app" in str(caught.value)
        assert "costs a week because nothing errors" in str(
            caught.value
        )

    def test_clean_outputs_pass_with_a_count(self):
        auditor = CaseAuditor(
            source_paths=(),
            output_paths=("bin/app", "lib/core.a"),
        )
        assert auditor.check_outputs() == "2 output(s) case-clean"


class TestDrift:
    def test_directory_spelling_drift_is_a_lower_temperature(self):
        auditor = CaseAuditor(
            source_paths=("Util/a.c", "util/b.c"),
            output_paths=(),
        )
        watch = auditor.drift_watch()
        assert len(watch) == 1
        assert watch[0].startswith("Util / util:")
        assert "a collision after the next refactor" in watch[0]

    def test_consistent_spelling_watches_nothing(self):
        auditor = CaseAuditor(
            source_paths=("util/a.c", "util/b.c"),
            output_paths=(),
        )
        assert auditor.drift_watch() == []
