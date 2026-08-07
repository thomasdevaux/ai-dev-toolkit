"""python -m tools.audit ..."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .checks import run_all


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.audit")
    parser.add_argument("--toolkit-root", default=".", help="path to the toolkit checkout (default: cwd)")
    args = parser.parse_args(argv)

    toolkit_root = Path(args.toolkit_root).resolve()
    result = run_all(toolkit_root)

    if not result.findings:
        print("No issues found.")
        return 0

    by_check: dict[str, list[str]] = {}
    for finding in result.findings:
        by_check.setdefault(finding.check, []).append(finding.message)

    for check, messages in by_check.items():
        print(f"[{check}]")
        for message in messages:
            print(f"  - {message}")

    return 1


if __name__ == "__main__":
    sys.exit(main())
