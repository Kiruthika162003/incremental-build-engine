"""Cross-repo dependencies: pinned by commit, aged in the open.

A build that reaches into a sibling repository must say exactly
which commit it means, because "the latest" is a different answer
every hour and a build that changes without a local edit is a
haunting. The pin book records each external repo's commit and
the tick it was pinned, updates are explicit two-step affairs, a
proposal showing what the move crosses, then an adoption, and the
age report is the pressure that keeps pins from fossilising: each
pin's staleness is measured in the commits it trails behind the
sibling's head, not in days, because a repo that idled for a
month costs nothing to trail while a repo that landed eighty
commits is eighty conflicts compounding. The pin that trails by
the most commits is the first line, since that is where the
eventual catch-up hurts most.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid, Missing


@dataclass
class SiblingRepo:
    name: str
    history: list[str] = field(default_factory=list)

    def land(self, commit: str) -> None:
        if commit in self.history:
            raise Invalid(f"{commit} already landed in {self.name}")
        self.history.append(commit)

    def head(self) -> str:
        if not self.history:
            raise Invalid(f"{self.name} has no commits")
        return self.history[-1]

    def trailing(self, commit: str) -> int:
        if commit not in self.history:
            raise Missing(
                f"{self.name} has no commit {commit}; the pin points "
                f"at nothing"
            )
        return len(self.history) - 1 - self.history.index(commit)


@dataclass
class PinBook:
    siblings: dict[str, SiblingRepo] = field(default_factory=dict)
    pins: dict[str, tuple[str, int]] = field(default_factory=dict)

    def track(self, repo: SiblingRepo) -> None:
        if repo.name in self.siblings:
            raise Invalid(f"{repo.name} is already tracked")
        self.siblings[repo.name] = repo

    def pin(self, name: str, commit: str, now: int) -> None:
        repo = self.siblings.get(name)
        if repo is None:
            raise Missing(f"no sibling named {name}")
        repo.trailing(commit)
        self.pins[name] = (commit, now)

    def propose_update(self, name: str) -> str:
        repo = self.siblings[name]
        commit, _ = self.pins[name]
        behind = repo.trailing(commit)
        if behind == 0:
            return f"{name} is at head; nothing to adopt"
        crossed = repo.history[
            repo.history.index(commit) + 1 :
        ]
        return (
            f"moving {name} from {commit} to {repo.head()} crosses "
            f"{behind} commits: {', '.join(crossed)}"
        )

    def adopt(self, name: str, now: int) -> None:
        repo = self.siblings[name]
        self.pins[name] = (repo.head(), now)

    def age_report(self) -> str:
        if not self.pins:
            raise Invalid("nothing is pinned")
        rows = []
        for name, (commit, _) in self.pins.items():
            behind = self.siblings[name].trailing(commit)
            rows.append((behind, name, commit))
        rows.sort(reverse=True)
        lines = [
            f"{name} at {commit}: trails head by {behind} commits"
            for behind, name, commit in rows
        ]
        worst = rows[0]
        if worst[0] > 0:
            lines.append(
                f"catch up {worst[1]} first; that is where the "
                f"conflicts are compounding"
            )
        return "\n".join(lines)
