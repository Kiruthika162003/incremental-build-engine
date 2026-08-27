from __future__ import annotations

import pytest

from forge.buildseal import seal_build
from forge.errors import Invalid
from forge.whydiffer import DivergenceCase

TOOLS = {"cc": "gcc-13.1"}
SHAPES = {"app": ()}


def base_case(**overrides) -> DivergenceCase:
    settings = {
        "our_seal": seal_build("tree-1", TOOLS, SHAPES),
        "their_seal": seal_build("tree-1", TOOLS, SHAPES),
        "shared_text_files": {},
        "our_commands": ["cc -DNDEBUG main.c"],
        "our_outputs": {"bin/app": "d1"},
        "their_outputs": {"bin/app": "d1"},
    }
    settings.update(overrides)
    return DivergenceCase(**settings)


class TestTheOrder:
    def test_a_seal_mismatch_ends_the_hunt_immediately(self):
        case = base_case(
            their_seal=seal_build("tree-2", TOOLS, SHAPES)
        )
        verdict = case.diagnose()
        assert verdict.startswith("the seal ends the hunt")
        assert "sources differ" in verdict
        assert "nothing else needed" in verdict

    def test_line_endings_are_the_second_suspect(self):
        case = base_case(
            shared_text_files={
                "main.c": (b"int x;\n", b"int x;\r\n")
            }
        )
        verdict = case.diagnose()
        assert verdict.startswith("line endings: main.c")
        assert "fix the checkout, not the build" in verdict
        assert "seal came back clean" in verdict

    def test_poison_flags_are_the_third_suspect(self):
        case = base_case(
            our_commands=["cc -DBUILD_TIME=now main.c"]
        )
        verdict = case.diagnose()
        assert verdict.startswith("flag hygiene:")
        assert "seal, line endings came back clean" in verdict

    def test_the_expensive_diff_runs_last(self):
        case = base_case(their_outputs={"bin/app": "OTHER"})
        verdict = case.diagnose()
        assert verdict.startswith("the expensive answer:")
        assert "starting with bin/app" in verdict
        assert "seal, line endings, flags came back clean" in (
            verdict
        )


class TestTheQuietCase:
    def test_agreement_lists_everything_checked(self):
        verdict = base_case().diagnose()
        assert verdict.startswith("no divergence found")
        assert "seal, line endings, flags, outputs" in verdict

    def test_real_content_drift_is_not_blamed_on_endings(self):
        case = base_case(
            shared_text_files={
                "main.c": (b"int x;\n", b"int y;\n")
            },
            their_outputs={"bin/app": "OTHER"},
        )
        assert case.diagnose().startswith("the expensive answer")

    def test_no_outputs_on_either_side_is_refused(self):
        case = base_case(our_outputs={}, their_outputs={})
        with pytest.raises(Invalid):
            case.diagnose()
