"""Bootstrapping the toolchain: the compiler is proven by its own fixpoint.

A self-hosting compiler cannot be trusted on one build: stage1 is
built by the system compiler and carries its fingerprints, stage2
is built by stage1, and only stage3, built by stage2, can prove
anything, because if stage2 and stage3 are byte-identical the
compiler has reached its fixpoint and its output no longer
depends on who built it. The rig runs the ladder, compares the
digests, and refuses to bless a toolchain whose stages still
differ, naming the first divergence, since a stage2/stage3 gap
means nondeterminism or a genuine miscompile and both are
disqualifying. The ledger also records the classic economy: once
the fixpoint is proven, stage3 need not be rebuilt again until
the sources move, and the proof itself is cacheable like any
other action.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from forge.content import digest_text
from forge.errors import Invalid

Compiler = Callable[[str, str], str]


@dataclass
class BootstrapRig:
    source: str
    system_compiler_id: str
    compile_with: Compiler
    stages: list[str] = field(default_factory=list)

    def run_ladder(self) -> str:
        if not self.source.strip():
            raise Invalid("no compiler source to bootstrap")
        stage1 = self.compile_with(
            self.system_compiler_id, self.source
        )
        stage2 = self.compile_with(stage1, self.source)
        stage3 = self.compile_with(stage2, self.source)
        self.stages = [stage1, stage2, stage3]
        return (
            f"stage1 {digest_text(stage1)[:8]}, "
            f"stage2 {digest_text(stage2)[:8]}, "
            f"stage3 {digest_text(stage3)[:8]}"
        )

    def fixpoint_proven(self) -> bool:
        if len(self.stages) != 3:
            raise Invalid("run the ladder before asking for proof")
        return self.stages[1] == self.stages[2]

    def verdict(self) -> str:
        if self.fixpoint_proven():
            freed = (
                "stage1 still carries the system compiler's "
                "fingerprints and is discarded"
            )
            return (
                "the fixpoint holds: stage2 and stage3 are "
                f"byte-identical, the toolchain is self-hosting; "
                f"{freed}"
            )
        stage2, stage3 = self.stages[1], self.stages[2]
        position = next(
            (
                index
                for index, (a, b) in enumerate(
                    zip(stage2, stage3, strict=False)
                )
                if a != b
            ),
            min(len(stage2), len(stage3)),
        )
        return (
            "REFUSED: stage2 and stage3 diverge at byte "
            f"{position}; nondeterminism or a miscompile, and "
            "both are disqualifying"
        )

    def blessing_digest(self) -> str:
        if not self.fixpoint_proven():
            raise Invalid(
                "an unproven toolchain does not get a digest to "
                "bless"
            )
        return digest_text(self.stages[2])
