"""Local patches over third-party sources: a stack that knows its base.

Every vendored dependency accumulates patches, the fix upstream
has not merged, the workaround for the platform upstream does not
own, and each patch is a promise made against a specific text.
The queue records that promise as the digest of the region the
patch expects, so when upstream moves, staleness is a lookup:
patches whose recorded context no longer matches the new base are
named stale by title, before anyone builds, instead of failing as
a fuzzy apply that lands the change three lines from where it
belonged. Application is ordered and all-or-nothing per patch,
each patch seeing the text its predecessors produced, because a
patch that applies with fuzz is a patch that lies, and the queue
would rather refuse loudly than succeed approximately.

One hazard survived measurement and stays recorded: the guess was
that renaming beta to brand-new-beta would make a beta patch
stale, but substring containment keeps it alive and it lands
inside the new name, producing brand-new-beta-fixed. Literal
patches cannot tell a word from a fragment, which is the entire
argument for writing the find with surrounding context lines: the
wider the quoted region, the harder it is for a rename to smuggle
the old text past the staleness check.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.content import digest_text
from forge.errors import Invalid, Stale


@dataclass(frozen=True)
class Patch:
    title: str
    find: str
    replace: str
    context_digest: str

    @classmethod
    def against(
        cls, base: str, title: str, find: str, replace: str
    ) -> Patch:
        if find not in base:
            raise Invalid(
                f"patch {title} targets text the base does not "
                "contain; it was written against something else"
            )
        if base.count(find) > 1:
            raise Invalid(
                f"patch {title} matches {base.count(find)} places; "
                "a patch that could land twice lands wrong"
            )
        return cls(
            title=title,
            find=find,
            replace=replace,
            context_digest=digest_text(find),
        )


@dataclass
class PatchQueue:
    patches: list[Patch] = field(default_factory=list)
    applied_titles: list[str] = field(default_factory=list)

    def add(self, patch: Patch) -> None:
        if any(p.title == patch.title for p in self.patches):
            raise Invalid(f"patch {patch.title} is already queued")
        self.patches.append(patch)

    def stale_against(self, base: str) -> list[str]:
        found = []
        text = base
        for patch in self.patches:
            if patch.find in text:
                text = text.replace(patch.find, patch.replace, 1)
            else:
                found.append(patch.title)
        return found

    def apply(self, base: str) -> str:
        stale = self.stale_against(base)
        if stale:
            raise Stale(
                f"{len(stale)} patch(es) no longer match the base: "
                f"{', '.join(stale)}; rebase them before building"
            )
        text = base
        for patch in self.patches:
            text = text.replace(patch.find, patch.replace, 1)
            self.applied_titles.append(patch.title)
        return text

    def rebase(self, patch_title: str, base: str) -> None:
        for index, patch in enumerate(self.patches):
            if patch.title == patch_title:
                if patch.find in base:
                    raise Invalid(
                        f"{patch_title} still applies; a rebase "
                        "it does not need would churn the digest "
                        "for nothing"
                    )
                self.patches.pop(index)
                return
        raise Invalid(f"no queued patch named {patch_title}")

    def ledger(self) -> str:
        if not self.patches:
            return "the queue is empty; upstream owns every line"
        lines = [f"{len(self.patches)} patch(es) queued"]
        lines.extend(
            f"  {patch.title} "
            f"(context {patch.context_digest[:8]})"
            for patch in self.patches
        )
        return "\n".join(lines)
