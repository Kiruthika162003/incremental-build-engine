from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.makeimport import import_makefile

CLEAN_MAKEFILE = """
.PHONY: all
all: app

app: main.o lib.o
\tld -o app main.o lib.o

main.o: main.c
\tcc -c main.c

lib.o: lib.c
\tcc -c lib.c
"""


class TestTranslation:
    def test_clean_rules_become_stanzas(self):
        parsed, report = import_makefile(CLEAN_MAKEFILE)
        assert sorted(parsed.stanzas) == ["app", "lib.o", "main.o"]
        assert parsed.stanzas["main.o"].command == "cc -c main.c"
        assert parsed.stanzas["app"].needs == ("main.o", "lib.o")
        assert report.grade().startswith("3/3 rules translated clean")

    def test_leaf_prerequisites_become_sources(self):
        parsed, _ = import_makefile(CLEAN_MAKEFILE)
        assert sorted(parsed.sources) == ["lib.c", "main.c"]

    def test_phony_targets_are_dropped_with_a_note(self):
        _, report = import_makefile(CLEAN_MAKEFILE)
        assert report.phony_dropped == ["all"]


class TestTheSubset:
    def test_pattern_rules_need_a_human_with_the_why(self):
        text = "%.o: %.c\n\tcc -c $<\n"
        _, report = import_makefile(text)
        assert len(report.needs_a_human) == 1
        assert "worse than broken" in report.needs_a_human[0]

    def test_variables_are_refused_not_mistranslated(self):
        text = "app: $(OBJS)\n\tld -o app\n"
        parsed, report = import_makefile(text)
        assert "app" not in parsed.stanzas
        assert report.needs_a_human

    def test_multiline_recipes_exceed_the_subset(self):
        text = "app: main.o\n\tcc -o app main.o\n\tstrip app\n"
        _, report = import_makefile(text)
        assert "2 recipe lines" in report.needs_a_human[0]

    def test_an_orphan_recipe_is_refused_loudly(self):
        with pytest.raises(Invalid, match="no rule above"):
            import_makefile("\tcc -c main.c\n")

    def test_the_grade_is_a_progress_number(self):
        text = CLEAN_MAKEFILE + "%.d: %.c\n\tmakedep $<\n"
        _, report = import_makefile(text)
        assert "3/4 rules translated clean (75%)" in report.grade()
