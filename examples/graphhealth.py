"""Graph health day: walls, diets, cycles, and the doctor's rounds.

Run with: python -m examples.graphhealth
"""

from __future__ import annotations

from forge.builddoctor import Clinic, diagnose
from forge.graph import Graph
from forge.packagecycles import PackageCycleAuditor
from forge.strictdeps import StrictChecker
from forge.visibility import VisibilityWall


def walls() -> None:
    graph = Graph()
    graph.declare("auth/internal")
    graph.declare("billing/charge", needs=("auth/internal",))
    wall = VisibilityWall(graph=graph)
    print("walls:")
    for line in wall.violations():
        print(f"  {line}")


def diets() -> None:
    checker = StrictChecker()
    checker.provides("jsonlib", ("parse",))
    checker.provides("httplib", ("http_get",))
    print("diets:")
    page = checker.diet(
        "app",
        declared_deps=("jsonlib", "httplib"),
        consumed_symbols=("parse",),
    )
    for line in page.splitlines():
        print(f"  {line}")


def cycles() -> None:
    graph = Graph()
    graph.declare("billing/types")
    graph.declare("auth/helper", needs=("billing/types",))
    graph.declare("billing/charge", needs=("auth/session",))
    graph.declare("auth/session")
    auditor = PackageCycleAuditor(graph=graph)
    print("cycles:")
    for line in auditor.audit().splitlines():
        print(f"  {line}")


def rounds() -> None:
    clinic = Clinic()
    prescription = diagnose(
        "auth/api",
        declared={"json", "oldlib"},
        scanned={"json", "crypto"},
        observed={"json", "crypto"},
    )
    clinic.file_visit(prescription)
    print("doctor:")
    for line in prescription.page().splitlines():
        print(f"  {line}")


def main() -> int:
    walls()
    diets()
    cycles()
    rounds()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
