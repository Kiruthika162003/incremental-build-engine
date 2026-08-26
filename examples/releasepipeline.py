"""The release pipeline: variants build, the stamp lands, the package ships.

Run with: python -m examples.releasepipeline
"""

from __future__ import annotations

from forge.installtree import InstallLayout, assemble, drift, layout_digest
from forge.stamps import stamped_tower


def build_and_stamp():
    project, tree = stamped_tower(units=3)
    cold = project.engine.build("release", tree)
    print(f"cold build:   {cold.line()}")
    restamp = project.restamp_and_build(tree, "v2.1.0")
    print(
        f"restamp:      ran {restamp.ran}, "
        f"quarantine {'holds' if project.quarantine_holds(restamp) else 'BROKEN'}"
    )
    return project, tree


def package(tree):
    layout = InstallLayout()
    layout.place("release", "bin/release")
    layout.place("unit0.o", "lib/unit0.o")
    receipt = assemble(layout, tree)
    print(f"install:      {receipt.line()}")
    digest = layout_digest(layout, tree)
    print(f"package id:   {digest}")
    return layout, digest


def compare(layout, tree):
    previous = {
        "bin/release": "0" * 32,
        "lib/unit0.o": tree.digest_of("dist/lib/unit0.o"),
    }
    moved = drift(previous, layout, tree)
    for line in moved:
        print(f"drift:        {line}")


def main() -> int:
    project, tree = build_and_stamp()
    layout, _ = package(tree)
    compare(layout, tree)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
