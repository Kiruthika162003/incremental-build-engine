"""Macros: one declaration becomes many stanzas, hygienically.

Every repository grows the same shape three hundred times, a
compile feeding a test feeding a report, and copying the shape by
hand copies its bugs by hand too. A macro captures the shape once:
given a name and parameters, it expands into concrete stanzas
before the graph ever sees them, so the engine stays ignorant of
macros entirely and everything downstream, caching, queries,
diffing, works on the expanded truth. Hygiene is the discipline
that keeps expansion safe: every generated stanza's name is
prefixed with the instantiation's own, collisions between two
instantiations are therefore impossible by construction, and a
macro that tries to reach outside its prefix is refused at
expansion, because a macro that names other people's targets is a
footgun with a template.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from forge.buildfile import Stanza
from forge.errors import Invalid

MacroBody = Callable[[str, dict], list[Stanza]]


@dataclass
class MacroRegistry:
    macros: dict[str, MacroBody] = field(default_factory=dict)
    expansions: int = 0

    def define(self, name: str, body: MacroBody) -> None:
        if name in self.macros:
            raise Invalid(f"macro {name} is already defined")
        self.macros[name] = body

    def expand(
        self, macro: str, instance: str, params: dict
    ) -> list[Stanza]:
        body = self.macros.get(macro)
        if body is None:
            raise Invalid(
                f"no macro named {macro}; defined are "
                f"{sorted(self.macros)}"
            )
        stanzas = body(instance, params)
        if not stanzas:
            raise Invalid(
                f"{macro}({instance}) expanded to nothing; an empty "
                f"macro is a typo with confidence"
            )
        prefix = f"{instance}."
        for stanza in stanzas:
            if not stanza.name.startswith(prefix):
                raise Invalid(
                    f"{macro}({instance}) produced {stanza.name}, "
                    f"outside its prefix {prefix}; macros name only "
                    f"their own"
                )
            for need in stanza.needs:
                internal = need.startswith(prefix)
                parameter = need in params.get("inputs", ())
                if not internal and not parameter:
                    raise Invalid(
                        f"{stanza.name} needs {need}, which is neither "
                        f"internal nor a declared input"
                    )
        self.expansions += 1
        return stanzas


def compile_test_report(instance: str, params: dict) -> list[Stanza]:
    """The shape every repository grows three hundred times."""
    source = params["inputs"][0]
    return [
        Stanza(
            name=f"{instance}.obj",
            command="cc",
            reads=(source,),
            writes=(f"{instance}.obj",),
            needs=(source,),
        ),
        Stanza(
            name=f"{instance}.test",
            command="runner",
            reads=(f"{instance}.obj",),
            writes=(f"{instance}.test",),
            needs=(f"{instance}.obj",),
        ),
        Stanza(
            name=f"{instance}.report",
            command="reporter",
            reads=(f"{instance}.test",),
            writes=(f"{instance}.report",),
            needs=(f"{instance}.test",),
        ),
    ]
