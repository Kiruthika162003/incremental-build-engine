"""A refactor week: the rename, the review, the walls, the prune.

Run with: python -m examples.refactorweek
"""

from __future__ import annotations

from forge.aliases import AliasBook
from forge.graph import Graph
from forge.graphdiff import review_page
from forge.ownership import OwnerBook
from forge.visibility import PUBLIC, VisibilityWall


def monday_rename() -> None:
    graph = Graph()
    graph.declare("network_lib")
    book = AliasBook(graph=graph)
    book.declare("netlib", "network_lib", expires=100)
    for caller in ("billing", "billing", "search"):
        book.resolve("netlib", caller, now=10)
    print("monday, the rename ships as an alias:")
    print(f"  {book.worklist(now=10)}")


def wednesday_review() -> None:
    before = Graph()
    before.declare("base")
    before.declare("app", needs=("base",))
    after = Graph()
    after.declare("base")
    after.declare("cache_layer")
    after.declare("app", needs=("base", "cache_layer"))
    print("wednesday, the BUILD review sees edges:")
    for line in review_page(before, after).splitlines():
        print(f"  {line}")


def thursday_walls() -> None:
    graph = Graph()
    graph.declare("auth/session")
    graph.declare("auth/internal")
    graph.declare("billing/charge", needs=("auth/internal",))
    wall = VisibilityWall(graph=graph)
    wall.declare("auth/session", PUBLIC)
    print("thursday, the wall holds:")
    for line in wall.violations():
        print(f"  {line}")


def friday_owners() -> None:
    owners = OwnerBook()
    owners.declare("auth", ("meera",))
    orphans, ghosts = owners.audit(
        ["auth", "search"], active_roster={"meera"}
    )
    print("friday, the roster audit:")
    print(f"  orphans: {orphans}, ghost-owned: {ghosts}")


def main() -> int:
    monday_rename()
    wednesday_review()
    thursday_walls()
    friday_owners()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
