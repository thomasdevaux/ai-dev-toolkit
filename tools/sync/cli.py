"""python -m tools.sync ..."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .detect import detect_stacks
from .manifest import ManifestError, baseline_entry_ids, load_manifest
from .status import build_status_report
from .sync import SyncBlocked, sync_entries


def _claude_dir(args: argparse.Namespace) -> Path:
    if args.user:
        return Path.home() / ".claude"
    project_dir = Path(args.project_dir) if args.project_dir else Path.cwd()
    return project_dir / ".claude"


def _cmd_sync(args: argparse.Namespace) -> int:
    toolkit_root = Path(args.toolkit_root).resolve()
    claude_dir = _claude_dir(args)
    entry_ids = args.entry_ids
    try:
        if not entry_ids:
            manifest = load_manifest(toolkit_root)
            scope = "user" if args.user else "project"
            entry_ids = baseline_entry_ids(manifest, scope)
            if not entry_ids:
                print(f"error: no entry_ids given and no tier:baseline entries found for scope '{scope}'", file=sys.stderr)
                return 1
            print(f"no entry_ids given - syncing all baseline entries: {', '.join(entry_ids)}")
        sync_entries(entry_ids, toolkit_root, claude_dir, auto_yes=args.yes)
    except (ManifestError, SyncBlocked) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def _cmd_detect(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir) if args.project_dir else Path.cwd()
    stacks = detect_stacks(project_dir)
    if not stacks:
        print("no known stack markers found")
    else:
        print("detected stack(s), suggested for review (not synced automatically):")
        for stack in stacks:
            print(f"  - {stack}")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    toolkit_root = Path(args.toolkit_root).resolve()
    project_dir = Path(args.project_dir) if args.project_dir else Path.cwd()
    claude_dir = project_dir / ".claude"
    try:
        report = build_status_report(toolkit_root, claude_dir, project_dir, for_hook=args.for_hook)
    except ManifestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if report:
        print(report)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m tools.sync")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser("sync", help="synchronize one or more manifest entries")
    sync_parser.add_argument("entry_ids", nargs="*", help="manifest entry id(s) to synchronize (default: every tier:baseline entry for the target scope)")
    sync_parser.add_argument("--toolkit-root", required=True, help="path to the toolkit checkout")
    sync_parser.add_argument("--project-dir", help="target project directory (default: cwd)")
    sync_parser.add_argument("--user", action="store_true", help="sync to ~/.claude/ instead of a project")
    sync_parser.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    sync_parser.set_defaults(func=_cmd_sync)

    detect_parser = subparsers.add_parser("detect", help="suggest tech stacks detected in a project")
    detect_parser.add_argument("--project-dir", help="project directory to scan (default: cwd)")
    detect_parser.set_defaults(func=_cmd_detect)

    status_parser = subparsers.add_parser("status", help="report sync drift and unsynced baseline/stack entries")
    status_parser.add_argument("--toolkit-root", required=True, help="path to the toolkit checkout")
    status_parser.add_argument("--project-dir", help="target project directory (default: cwd)")
    status_parser.add_argument("--for-hook", action="store_true", help="report only what's worth interrupting a session for; print nothing when there isn't any")
    status_parser.set_defaults(func=_cmd_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
