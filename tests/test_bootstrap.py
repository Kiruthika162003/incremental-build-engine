from __future__ import annotations

import pytest

from forge.bootstrap import BootstrapRig
from forge.errors import Invalid

SOURCE = "compiler: fold constants, emit tight loops"


def honest_compiler(compiler_id: str, source: str) -> str:
    if compiler_id == "system-gcc":
        return f"binary({source})|codegen=roomy"
    return f"binary({source})|codegen=tight"


def haunted_compiler(compiler_id: str, source: str) -> str:
    return f"binary({source})|built-by={compiler_id}"


class TestTheLadder:
    def test_the_ladder_reports_three_digests(self):
        rig = BootstrapRig(
            source=SOURCE,
            system_compiler_id="system-gcc",
            compile_with=honest_compiler,
        )
        report = rig.run_ladder()
        assert report.count("stage") == 3

    def test_empty_source_is_refused(self):
        rig = BootstrapRig(
            source="  ",
            system_compiler_id="system-gcc",
            compile_with=honest_compiler,
        )
        with pytest.raises(Invalid):
            rig.run_ladder()

    def test_proof_before_the_ladder_is_refused(self):
        rig = BootstrapRig(
            source=SOURCE,
            system_compiler_id="system-gcc",
            compile_with=honest_compiler,
        )
        with pytest.raises(Invalid):
            rig.fixpoint_proven()


class TestTheFixpoint:
    def test_the_honest_compiler_reaches_its_fixpoint(self):
        rig = BootstrapRig(
            source=SOURCE,
            system_compiler_id="system-gcc",
            compile_with=honest_compiler,
        )
        rig.run_ladder()
        assert rig.fixpoint_proven()
        verdict = rig.verdict()
        assert "byte-identical" in verdict
        assert "stage1 still carries" in verdict

    def test_the_haunted_compiler_is_refused_with_the_byte(self):
        rig = BootstrapRig(
            source=SOURCE,
            system_compiler_id="system-gcc",
            compile_with=haunted_compiler,
        )
        rig.run_ladder()
        assert not rig.fixpoint_proven()
        verdict = rig.verdict()
        assert verdict.startswith("REFUSED")
        assert "diverge at byte" in verdict

    def test_only_a_proven_toolchain_gets_blessed(self):
        rig = BootstrapRig(
            source=SOURCE,
            system_compiler_id="system-gcc",
            compile_with=haunted_compiler,
        )
        rig.run_ladder()
        with pytest.raises(Invalid):
            rig.blessing_digest()

    def test_the_blessing_is_the_stage3_digest(self):
        rig = BootstrapRig(
            source=SOURCE,
            system_compiler_id="system-gcc",
            compile_with=honest_compiler,
        )
        rig.run_ladder()
        assert len(rig.blessing_digest()) == 32
