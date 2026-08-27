"""Documentation code is code: fenced samples compile or the docs are fiction.

Every README promises that its snippets work, and every README is
eventually lying, because the code moved and the prose did not.
The drill extracts fenced samples from documentation, runs each
through a checker the caller supplies, the real loader, the real
compiler front end, and reports rot by file and line, quoting the
first error, so the fix is a jump, not a search. Samples can opt
out with a no-check fence tag, but the ledger counts the
opt-outs, since a document whose samples are mostly unchecked has
not passed the drill, it has dodged it, and the report says which
of the two happened.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from forge.errors import Invalid

Checker = Callable[[str], str | None]
FENCE = "```"
SKIP_TAG = "no-check"


@dataclass(frozen=True)
class Sample:
    doc: str
    line: int
    body: str
    checked: bool


def extract(doc_name: str, text: str) -> list[Sample]:
    samples = []
    lines = text.splitlines()
    inside = False
    start = 0
    checked = True
    held: list[str] = []
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith(FENCE):
            if not inside:
                inside = True
                start = number
                checked = SKIP_TAG not in stripped
                held = []
            else:
                inside = False
                samples.append(
                    Sample(
                        doc=doc_name,
                        line=start,
                        body="\n".join(held),
                        checked=checked,
                    )
                )
        elif inside:
            held.append(line)
    if inside:
        raise Invalid(
            f"{doc_name}: a fence opened at line {start} and "
            "never closed"
        )
    return samples


def drill(
    docs: dict[str, str], check: Checker
) -> tuple[list[str], int, int]:
    rotted = []
    checked_count = 0
    dodged = 0
    for doc_name in sorted(docs):
        for sample in extract(doc_name, docs[doc_name]):
            if not sample.checked:
                dodged += 1
                continue
            checked_count += 1
            error = check(sample.body)
            if error is not None:
                rotted.append(
                    f"{sample.doc}:{sample.line}: {error}"
                )
    return rotted, checked_count, dodged


def report(docs: dict[str, str], check: Checker) -> str:
    if not docs:
        raise Invalid("no documents to drill")
    rotted, checked_count, dodged = drill(docs, check)
    total = checked_count + dodged
    if total == 0:
        return "no samples found; the docs promise nothing"
    lines = [
        f"{checked_count} sample(s) checked, {len(rotted)} "
        f"rotted, {dodged} opted out"
    ]
    lines.extend(f"  {entry}" for entry in rotted)
    if dodged > checked_count:
        lines.append(
            "  most samples are unchecked: the docs did not "
            "pass the drill, they dodged it"
        )
    return "\n".join(lines)
