"""The command line: the audits and their verdicts on demand."""

from __future__ import annotations

import argparse
import sys

from forge.audits.registry import broken, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="forge")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("audits", help="run every audit and print the page")
    commands.add_parser("check", help="exit nonzero if any audit is broken")
    commands.add_parser(
        "summary", help="one line: audits and their verdict"
    )
    parsed = parser.parse_args(argv)
    if parsed.command == "audits":
        print(report())
        return 0
    if parsed.command == "summary":
        from forge.audits.registry import AUDITS

        failing = broken()
        print(
            f"{len(AUDITS)} audits ({len(failing)} broken)"
        )
        return 1 if failing else 0
    failing = broken()
    if failing:
        print(f"broken: {', '.join(failing)}")
        return 1
    print("all audits hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
