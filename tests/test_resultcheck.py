from __future__ import annotations

import pytest

from forge.errors import Invalid
from forge.resultcheck import Validator, magic, nonempty
from forge.workspace import Workspace


def world() -> Workspace:
    tree = Workspace()
    tree.write("good.o", b"\x7fELFvalid object body")
    tree.write("empty.o", b"")
    tree.write("truncated.o", b"garbage without magic")
    return tree


class TestChecks:
    def test_nonempty_is_the_floor(self):
        assert nonempty(b"") == "the output is empty"
        assert nonempty(b"x") is None

    def test_magic_catches_the_truncated_write(self):
        check = magic(b"\x7fELF")
        assert check(b"\x7fELFrest") is None
        assert "truncated" in check(b"gar")


class TestValidation:
    def test_a_good_result_passes_and_is_counted(self):
        validator = Validator()
        validator.require("good.o", magic(b"\x7fELF"))
        validator.validate("good.o", world())
        assert validator.passed == 1

    def test_the_empty_artifact_is_refused_before_the_cache(self):
        validator = Validator()
        with pytest.raises(Invalid, match="never cached"):
            validator.validate("empty.o", world())

    def test_the_refusal_names_the_check(self):
        validator = Validator()
        validator.require("truncated.o", magic(b"\x7fELF"))
        with pytest.raises(Invalid, match="magic bytes"):
            validator.validate("truncated.o", world())

    def test_validate_all_stops_at_the_first_failure(self):
        validator = Validator()
        with pytest.raises(Invalid):
            validator.validate_all(("good.o", "empty.o"), world())
        assert validator.passed == 1

    def test_custom_predicates_carry_format_knowledge(self):
        def has_symbol_table(payload: bytes) -> str | None:
            if b"body" not in payload:
                return "no symbol table section"
            return None

        validator = Validator()
        validator.require("good.o", has_symbol_table)
        validator.validate("good.o", world())

    def test_the_salary_counts_the_saves(self):
        validator = Validator()
        for path in ("empty.o", "truncated.o"):
            validator.require(path, magic(b"\x7fELF"))
            with pytest.raises(Invalid):
                validator.validate(path, world())
        validator.validate("good.o", world())
        assert validator.salary() == (
            "2 results exited zero and were still refused; 1 passed"
        )
