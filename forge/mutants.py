"""Mutation testing: the tests are tested, and the survivors name the holes.

A test suite with high coverage and low power is a common
tragedy: every line is executed, nothing is actually checked.
Mutation testing measures power instead of reach: plant a
deliberate bug, a flipped comparison, an off-by-one, a dropped
call, run the suite, and demand red. A killed mutant is the
suite working; a surviving mutant is a named hole, this exact
bug would ship today, which is a sharper sentence than any
coverage percentage. The score is kills over mutants, and the
report refuses the classic consolation: a survivor in dead
code is still reported, flagged as possibly-dead-code, because
"the mutant survived where nothing runs" and "the mutant
survived where nothing checks" are different findings and
only one of them is comfortable. The budget is respected,
mutation runs are whole suite runs, so the planner samples
mutants per file rather than exhausting them, and says so.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from forge.errors import Invalid

Suite = Callable[[str], bool]


@dataclass(frozen=True)
class Mutant:
    target_file: str
    description: str
    mutant_id: str


@dataclass
class MutationRun:
    suite_fails_on: Suite
    killed: list[str] = field(default_factory=list)
    survivors: list[Mutant] = field(default_factory=list)
    suite_runs: int = 0

    def test_mutant(self, mutant: Mutant) -> str:
        self.suite_runs += 1
        if self.suite_fails_on(mutant.mutant_id):
            self.killed.append(mutant.mutant_id)
            return f"{mutant.mutant_id} killed; the suite works"
        self.survivors.append(mutant)
        return (
            f"{mutant.mutant_id} SURVIVED: "
            f"{mutant.description} in {mutant.target_file} "
            "would ship today"
        )

    def score(self) -> float:
        total = len(self.killed) + len(self.survivors)
        if total == 0:
            raise Invalid("no mutants were run")
        return len(self.killed) / total

    def report(
        self, dead_code_files: frozenset[str] = frozenset()
    ) -> str:
        total = len(self.killed) + len(self.survivors)
        lines = [
            f"{len(self.killed)} of {total} mutant(s) killed "
            f"({self.score():.0%}), {self.suite_runs} suite "
            "run(s) spent"
        ]
        for mutant in self.survivors:
            note = (
                " (possibly dead code: survived where nothing "
                "runs, which is a different finding from "
                "survived where nothing checks)"
                if mutant.target_file in dead_code_files
                else ""
            )
            lines.append(
                f"  hole: {mutant.description} in "
                f"{mutant.target_file}{note}"
            )
        return "\n".join(lines)


def sample_plan(
    mutants_per_file: dict[str, int], budget_runs: int
) -> str:
    if budget_runs < 1:
        raise Invalid("no budget, no mutants")
    total = sum(mutants_per_file.values())
    if total <= budget_runs:
        return (
            f"run all {total} mutant(s); the budget of "
            f"{budget_runs} covers exhaustion"
        )
    per_file = max(1, budget_runs // max(len(mutants_per_file), 1))
    return (
        f"sample {per_file} per file for "
        f"{len(mutants_per_file)} file(s): {total} mutant(s) "
        f"exceed the budget of {budget_runs}, and the report "
        "says so instead of implying exhaustion"
    )
