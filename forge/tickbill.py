"""The tick bill by rule class: the build got slower, and here is who ordered what.

"The build is twenty percent slower this month" is a fact
without a defendant until the ticks are grouped by rule class
and compared across periods: compiles, links, tests, codegen,
each with its own bill in both months, so the growth has an
address. The report ranks classes by their share of the growth,
splits each class's change into volume, more actions of the
same kind, against unit cost, the same actions getting
individually slower, because the two have different owners: a
volume bill belongs to whoever grew the graph and is usually
healthy, a unit-cost bill belongs to the toolchain or the
inputs and is usually rot. Shrinking classes are printed too,
as credits, since a report that only shows debits reads as an
accusation instead of a ledger and gets ignored accordingly.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.errors import Invalid


@dataclass(frozen=True)
class ClassBill:
    rule_class: str
    actions: int
    total_ticks: int

    def unit_cost(self) -> float:
        if self.actions == 0:
            raise Invalid(
                f"{self.rule_class} billed ticks with no actions"
            )
        return self.total_ticks / self.actions


def compare_months(
    before: dict[str, ClassBill], after: dict[str, ClassBill]
) -> str:
    if not before or not after:
        raise Invalid("both months need bills")
    total_before = sum(b.total_ticks for b in before.values())
    total_after = sum(b.total_ticks for b in after.values())
    growth = total_after - total_before
    rows = []
    for rule_class in sorted(set(before) | set(after)):
        old = before.get(
            rule_class, ClassBill(rule_class, 0, 0)
        )
        new = after.get(rule_class, ClassBill(rule_class, 0, 0))
        delta = new.total_ticks - old.total_ticks
        if delta == 0:
            continue
        if old.actions and new.actions:
            volume_part = round(
                (new.actions - old.actions) * old.unit_cost()
            )
            unit_part = delta - volume_part
            split = (
                f"volume {volume_part:+}, unit cost "
                f"{unit_part:+}"
            )
        else:
            split = "new or retired class"
        rows.append((delta, rule_class, split))
    rows.sort(reverse=True)
    percent = (
        f"{100 * growth / total_before:+.0f}%"
        if total_before
        else "n/a"
    )
    lines = [
        f"{total_before} -> {total_after} tick(s) ({percent})"
    ]
    for delta, rule_class, split in rows:
        label = "debit" if delta > 0 else "credit"
        lines.append(
            f"  {label} {rule_class}: {delta:+} ({split})"
        )
    if growth > 0 and rows:
        top_delta, top_class, top_split = rows[0]
        share = 100 * top_delta // growth
        lines.append(
            f"the growth has an address: {top_class} carries "
            f"{share}% of it, split {top_split}"
        )
    return "\n".join(lines)
