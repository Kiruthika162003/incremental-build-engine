"""Generated code: one schema in, a fan of outputs out, all or none.

A schema compiler takes one interface definition and emits a fan
of files, a message class per type, and the fan's width is decided
by the input's content, which breaks the assumption every other
rule enjoys: the output set is not known until the rule runs. The
generator declares an output directory instead of output names,
the fan lands under it atomically, and the manifest of what was
generated is itself an output with a stable name so downstream
rules can depend on the fan through the manifest without guessing
file names. Stale sweep is the half everyone forgets: when a type
is deleted from the schema, its generated file must leave too, or
the build links yesterday's class forever, so the generator diffs
the new fan against the manifest and removes what fell out, with
the sweep counted in the receipt.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.errors import Invalid
from forge.workspace import Workspace

MANIFEST_SUFFIX = "manifest"


@dataclass
class GenerationReceipt:
    generated: list[str] = field(default_factory=list)
    swept: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)

    def line(self) -> str:
        return (
            f"{len(self.generated)} generated, "
            f"{len(self.unchanged)} unchanged, {len(self.swept)} swept"
        )


@dataclass
class SchemaGenerator:
    schema_path: str
    out_dir: str

    def _manifest_path(self) -> str:
        return f"{self.out_dir}/{MANIFEST_SUFFIX}"

    def _parse_types(self, tree: Workspace) -> list[str]:
        text = tree.read_text(self.schema_path)
        types = []
        for raw in text.splitlines():
            line = raw.strip()
            if line.startswith("type "):
                name = line.split()[1]
                if name in types:
                    raise Invalid(
                        f"type {name} is declared twice in "
                        f"{self.schema_path}"
                    )
                types.append(name)
        if not types:
            raise Invalid(
                f"{self.schema_path} declares no types; a generator "
                f"with nothing to generate is a mistake upstream"
            )
        return types

    def _old_fan(self, tree: Workspace) -> list[str]:
        if not tree.exists(self._manifest_path()):
            return []
        return [
            line
            for line in tree.read_text(self._manifest_path()).splitlines()
            if line
        ]

    def generate(self, tree: Workspace) -> GenerationReceipt:
        receipt = GenerationReceipt()
        types = self._parse_types(tree)
        old = set(self._old_fan(tree))
        fresh = []
        for name in types:
            path = f"{self.out_dir}/{name.lower()}.gen"
            body = f"class {name} generated from {self.schema_path}"
            if tree.exists(path) and tree.read_text(path) == body:
                receipt.unchanged.append(path)
            else:
                tree.write_text(path, body)
                receipt.generated.append(path)
            fresh.append(path)
        for stale in sorted(old - set(fresh)):
            if tree.exists(stale):
                tree.delete(stale)
            receipt.swept.append(stale)
        tree.write_text(self._manifest_path(), "\n".join(fresh))
        return receipt

    def fan(self, tree: Workspace) -> list[str]:
        return self._old_fan(tree)
