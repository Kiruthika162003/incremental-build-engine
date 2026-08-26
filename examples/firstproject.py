"""A first project: cold build, warm build, one edit, one restamp.

Run with: python -m examples.firstproject
"""

from __future__ import annotations

from forge.loader import load
from forge.workspace import Workspace

PROJECT = """
source = main.c
source = util.c
source = format.c

rule = main.o
command = cc -O2
reads = main.c
writes = main.o
needs = main.c

rule = util.o
command = cc -O2
reads = util.c
writes = util.o
needs = util.c

rule = format.o
command = cc -O2
reads = format.c
writes = format.o
needs = format.c

rule = libcore
command = ar rcs
reads = util.o, format.o
writes = libcore
needs = util.o, format.o

rule = app
command = ld
reads = main.o, libcore
writes = app
needs = main.o, libcore
cost = 5
"""


def main() -> int:
    engine = load(PROJECT)
    tree = Workspace()
    tree.write_text("main.c", "int main;")
    tree.write_text("util.c", "int util;")
    tree.write_text("format.c", "int format;")

    cold = engine.build("app", tree)
    print(f"cold:  {cold.line()}")

    warm = engine.build("app", tree)
    print(f"warm:  {warm.line()}")

    tree.write_text("util.c", "int util; // tweaked")
    edited = engine.build("app", tree)
    print(f"edit:  {edited.line()}")
    print(f"       ran {', '.join(edited.ran)}; main.o untouched")

    print(f"cache: {engine.cache.ledger()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
