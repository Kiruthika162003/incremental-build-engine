"""Suite latency budgets: every directory owns its share of the wait.

Test suites do not get slow in one commit; they get slow at
thirty milliseconds a week, spread thin enough that no single
review notices. The budget makes the drift somebody's problem by
assigning each directory a latency allowance and metering actual
spend against it, so the report names overdrafts by owner instead
of announcing that "the suite" is slow, which is an accusation
against everyone and therefore no one. New tests are taxed at
admission: a test slower than the directory's per-test norm must
say why in a waiver, and the waiver list is printed with the
report, because the difference between a slow test with a reason
and a slow test with a shrug is the entire culture of a fast
suite. The overdraft verdict includes the cheapest path back
under budget, the biggest single test to speed up or shard.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid


@dataclass
class DirectoryBudget:
    directory: str
    allowance_ms: int
    per_test_norm_ms: int
    tests: dict[str, int] = field(default_factory=dict)
    waivers: dict[str, str] = field(default_factory=dict)

    def admit(
        self, test: str, cost_ms: int, waiver: str = ""
    ) -> str:
        if cost_ms < 0:
            raise Invalid(f"{test} cannot cost negative time")
        if test in self.tests:
            raise Invalid(f"{test} is already admitted")
        if cost_ms > self.per_test_norm_ms and not waiver:
            raise Invalid(
                f"{test} costs {cost_ms}ms against a norm of "
                f"{self.per_test_norm_ms}ms; slow is admissible, "
                "shrugging is not: write the waiver"
            )
        self.tests[test] = cost_ms
        if waiver:
            self.waivers[test] = waiver
        return f"{test} admitted at {cost_ms}ms"

    def spend(self) -> int:
        return sum(self.tests.values())

    def report(self) -> str:
        spend = self.spend()
        if spend <= self.allowance_ms:
            headroom = self.allowance_ms - spend
            line = (
                f"{self.directory}: {spend}ms of "
                f"{self.allowance_ms}ms ({headroom}ms headroom)"
            )
        else:
            overdraft = spend - self.allowance_ms
            biggest = max(
                self.tests.items(), key=lambda row: row[1]
            )
            line = (
                f"{self.directory}: OVERDRAFT {overdraft}ms "
                f"({spend}ms of {self.allowance_ms}ms); cheapest "
                f"path back: speed up or shard {biggest[0]} "
                f"({biggest[1]}ms)"
            )
        for test in sorted(self.waivers):
            line += (
                f"\n  waiver: {test}: {self.waivers[test]}"
            )
        return line


def suite_report(budgets: list[DirectoryBudget]) -> str:
    if not budgets:
        raise Invalid("no directories in the suite")
    overdrafts = [
        budget
        for budget in budgets
        if budget.spend() > budget.allowance_ms
    ]
    lines = [
        f"{len(budgets)} directories, {len(overdrafts)} in "
        "overdraft"
    ]
    for budget in sorted(
        budgets,
        key=lambda held: held.allowance_ms - held.spend(),
    ):
        lines.append(budget.report())
    return "\n".join(lines)
