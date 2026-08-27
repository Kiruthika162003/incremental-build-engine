"""Why did that rebuild: an explanation chain, not a shrug.

A build that reruns something expensive owes the developer a
sentence, because a team that cannot get the sentence invents
superstitions, deletes output directories, and blames the phase
of the moon. The explainer records each build's action shots,
command, input digests, outputs, and answers the only question
that matters after a slow rebuild: what changed. The answer is a
chain, not a fact: app relinked because libcore.o changed, and
libcore.o recompiled because core.c was edited, and the chain
ends at a file no recorded action produces, which is the root
cause. A target whose shot did not change gets the honest
inversion: nothing changed, so a rerun would be the cache's
failure, not the graph's.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid, Missing


@dataclass(frozen=True)
class ActionShot:
    command: str
    inputs: tuple[tuple[str, str], ...]
    outputs: tuple[str, ...]


@dataclass
class RebuildExplainer:
    builds: list[dict[str, ActionShot]] = field(default_factory=list)

    def record(self, shots: dict[str, ActionShot]) -> None:
        if not shots:
            raise Invalid("a build with no actions is not a build")
        self.builds.append(dict(shots))

    def _pair(
        self, target: str
    ) -> tuple[ActionShot | None, ActionShot]:
        if len(self.builds) < 2:
            raise Invalid("an explanation needs two builds")
        after = self.builds[-1].get(target)
        if after is None:
            raise Missing(f"{target} is not in the latest build")
        return self.builds[-2].get(target), after

    def _producer_of(self, path: str) -> str | None:
        for name, shot in self.builds[-1].items():
            if path in shot.outputs:
                return name
        return None

    def explain(self, target: str) -> str:
        return "\n".join(self._chain(target, seen=set()))

    def _chain(self, target: str, seen: set[str]) -> list[str]:
        if target in seen:
            return [f"{target}: already explained above"]
        seen.add(target)
        before, after = self._pair(target)
        if before is None:
            return [f"{target} ran because it had never been built"]
        if before.command != after.command:
            return [
                f"{target} ran because its command changed",
                f"  was: {before.command}",
                f"  now: {after.command}",
            ]
        if before.outputs != after.outputs:
            return [
                f"{target} ran because its output set changed "
                f"from {list(before.outputs)} to {list(after.outputs)}"
            ]
        old_inputs = dict(before.inputs)
        new_inputs = dict(after.inputs)
        added = sorted(set(new_inputs) - set(old_inputs))
        removed = sorted(set(old_inputs) - set(new_inputs))
        if added or removed:
            pieces = []
            if added:
                pieces.append(f"gained inputs {added}")
            if removed:
                pieces.append(f"lost inputs {removed}")
            return [f"{target} ran because it {' and '.join(pieces)}"]
        changed = sorted(
            path
            for path in new_inputs
            if new_inputs[path] != old_inputs[path]
        )
        if not changed:
            return [
                f"{target} had no reason to run: nothing changed, "
                "so a rerun would be the cache's failure, not the "
                "graph's"
            ]
        lines = []
        for path in changed:
            producer = self._producer_of(path)
            if producer is None:
                lines.append(
                    f"{target} ran because {path} was edited "
                    "(root cause)"
                )
            else:
                lines.append(
                    f"{target} ran because {path} changed, "
                    f"which {producer} produced"
                )
                lines.extend(
                    "  " + line
                    for line in self._chain(producer, seen)
                )
        return lines

    def root_causes(self, target: str) -> list[str]:
        story = self.explain(target)
        found = []
        for line in story.splitlines():
            if "(root cause)" in line:
                path = line.split(" ran because ")[1].split(
                    " was edited"
                )[0]
                found.append(path)
        return sorted(set(found))
