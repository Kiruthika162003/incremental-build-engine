"""Why do our builds differ: a decision tree instead of a shrug.

"It builds differently on my machine" opens a debugging session
with too many suspects, and the order you question them in is
most of the runtime. The diagnostician walks the suspects from
cheapest to most likely guilty: the build seal first, because a
seal mismatch names its own part and ends the hunt; then line
endings, because checkout normalization is the commonest quiet
divergence; then flag hygiene, because clock macros and
absolute paths poison per-machine; and only then the slow
answer, a full output diff, because paying the expensive check
first is how afternoons vanish. The verdict quotes the first
check that found something, with the checks that came back
clean listed as alibis, since the next engineer should not
re-interrogate suspects this run already cleared.
"""

from __future__ import annotations

from dataclasses import dataclass

from forge.buildseal import BuildSeal, compare
from forge.errors import Invalid
from forge.flaghygiene import audit as flag_audit
from forge.inputnorm import normalized_digest


@dataclass
class DivergenceCase:
    our_seal: BuildSeal
    their_seal: BuildSeal
    shared_text_files: dict[str, tuple[bytes, bytes]]
    our_commands: list[str]
    our_outputs: dict[str, str]
    their_outputs: dict[str, str]

    def diagnose(self) -> str:
        alibis = []
        seal_verdict = compare(self.our_seal, self.their_seal)
        if not seal_verdict.startswith("same build"):
            return (
                f"the seal ends the hunt: {seal_verdict}\n"
                "checked: nothing else needed"
            )
        alibis.append("seal")
        for path, (ours, theirs) in sorted(
            self.shared_text_files.items()
        ):
            if ours != theirs and normalized_digest(
                path, ours
            ) == normalized_digest(path, theirs):
                return (
                    f"line endings: {path} differs only in "
                    "checkout normalization; fix the checkout, "
                    "not the build\n"
                    f"checked: {', '.join(alibis)} came back clean"
                )
        alibis.append("line endings")
        for command in self.our_commands:
            complaints = flag_audit(command)
            if complaints:
                return (
                    f"flag hygiene: {complaints[0].line()}\n"
                    f"checked: {', '.join(alibis)} came back clean"
                )
        alibis.append("flags")
        differing = sorted(
            path
            for path in self.our_outputs
            if self.their_outputs.get(path)
            != self.our_outputs[path]
        )
        if differing:
            return (
                f"the expensive answer: {len(differing)} "
                f"output(s) genuinely differ, starting with "
                f"{differing[0]}; this is a real divergence, "
                "not an environment one\n"
                f"checked: {', '.join(alibis)} came back clean"
            )
        if self.our_outputs == {} and self.their_outputs == {}:
            raise Invalid("no outputs to compare on either side")
        return (
            "no divergence found: the builds agree everywhere "
            f"this case looked\nchecked: {', '.join(alibis)}, "
            "outputs"
        )
