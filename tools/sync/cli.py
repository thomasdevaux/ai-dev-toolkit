"""python -m tools.sync ..."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .detect import detect_stacks
from .manifest import ManifestError, baseline_entry_ids, load_manifest
from .state import load_state, save_state
from .status import build_hook_report, build_status_report
from .sync import SyncBlocked, switch_choice_group, sync_entries


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
        sync_entries(entry_ids, toolkit_root, claude_dir, auto_yes=args.yes, auto_yes_except_user_tools=args.yes_except_user_tools)
    except (ManifestError, SyncBlocked) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def _cmd_switch(args: argparse.Namespace) -> int:
    toolkit_root = Path(args.toolkit_root).resolve()
    claude_dir = _claude_dir(args)
    try:
        switch_choice_group(args.group, args.entry_id, toolkit_root, claude_dir, auto_yes=args.yes)
    except (ManifestError, SyncBlocked) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def _cmd_dismiss(args: argparse.Namespace) -> int:
    """Stop offering an entry in the discovery sections. Deliberately a CLI
    command rather than something the agent hand-edits into the state file:
    .toolkit-sync-state is sync's source of truth, and every other write to it
    goes through this package."""
    toolkit_root = Path(args.toolkit_root).resolve()
    claude_dir = _claude_dir(args)
    try:
        manifest = load_manifest(toolkit_root)
    except ManifestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    unknown = [entry_id for entry_id in args.entry_ids if entry_id not in manifest]
    if unknown:
        print(f"error: unknown entry id(s): {', '.join(unknown)}", file=sys.stderr)
        return 1

    state = load_state(claude_dir)
    dismissed = set(state.dismissed)
    if args.undo:
        # Re-offering something is the reversible half of the same decision;
        # without it a mistyped dismiss is only fixable by hand-editing the
        # very file this command exists to keep out of hands.
        changed = sorted(dismissed & set(args.entry_ids))
        dismissed -= set(args.entry_ids)
        verb = "will be offered again"
    else:
        changed = sorted(set(args.entry_ids) - dismissed)
        dismissed |= set(args.entry_ids)
        verb = "dismissed"

    state.dismissed = sorted(dismissed)
    save_state(claude_dir, state)
    if not changed:
        print("nothing to change")
        return 0
    print(f"{', '.join(changed)}: {verb}")
    return 0


def _cmd_detect(args: argparse.Namespace) -> int:
    toolkit_root = Path(args.toolkit_root).resolve()
    project_dir = Path(args.project_dir) if args.project_dir else Path.cwd()
    try:
        stacks = detect_stacks(project_dir, toolkit_root)
    except ManifestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not stacks:
        print("no known stack markers found")
    else:
        print("detected entry id(s), suggested for review (not synced automatically):")
        for stack in stacks:
            print(f"  - {stack}")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    toolkit_root = Path(args.toolkit_root).resolve()
    project_dir = Path(args.project_dir) if args.project_dir else Path.cwd()
    try:
        # The hook's plain call (no --user) covers both scopes in one process
        # — see build_hook_report's docstring. --user still reports only on
        # ~/.claude, for someone explicitly asking about that scope.
        if args.for_hook and not args.user:
            report = build_hook_report(toolkit_root, project_dir)
        else:
            claude_dir = _claude_dir(args)
            scope = "user" if args.user else "project"
            report = build_status_report(toolkit_root, claude_dir, project_dir, for_hook=args.for_hook, scope=scope)
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
    sync_parser.add_argument("--yes-except-user-tools", action="store_true", help="skip the confirmation prompt, except for entries sourced from user-tools/ (e.g. the statusline)")
    sync_parser.set_defaults(func=_cmd_sync)

    switch_parser = subparsers.add_parser("switch", help="adopt a different member of a choice-group (e.g. project-type)")
    switch_parser.add_argument("group", help="choice-group name, e.g. 'project-type'")
    switch_parser.add_argument("entry_id", help="the group member to adopt, e.g. 'project-type-app'")
    switch_parser.add_argument("--toolkit-root", required=True, help="path to the toolkit checkout")
    switch_parser.add_argument("--project-dir", help="target project directory (default: cwd)")
    switch_parser.add_argument("--user", action="store_true", help="switch in ~/.claude/ instead of a project")
    switch_parser.add_argument("--yes", action="store_true", help="skip the confirmation prompts, including the prune of the outgoing member's files")
    switch_parser.set_defaults(func=_cmd_switch)

    dismiss_parser = subparsers.add_parser("dismiss", help="stop offering an entry in status' discovery sections")
    dismiss_parser.add_argument("entry_ids", nargs="+", help="manifest entry id(s) to stop offering")
    dismiss_parser.add_argument("--toolkit-root", required=True, help="path to the toolkit checkout")
    dismiss_parser.add_argument("--project-dir", help="target project directory (default: cwd)")
    dismiss_parser.add_argument("--user", action="store_true", help="record the decision in ~/.claude/ instead of a project")
    dismiss_parser.add_argument("--undo", action="store_true", help="offer the entry again instead of dismissing it")
    dismiss_parser.set_defaults(func=_cmd_dismiss)

    detect_parser = subparsers.add_parser("detect", help="suggest tech stacks detected in a project")
    detect_parser.add_argument("--toolkit-root", required=True, help="path to the toolkit checkout")
    detect_parser.add_argument("--project-dir", help="project directory to scan (default: cwd)")
    detect_parser.set_defaults(func=_cmd_detect)

    status_parser = subparsers.add_parser("status", help="report sync drift and unsynced baseline/stack entries")
    status_parser.add_argument("--toolkit-root", required=True, help="path to the toolkit checkout")
    status_parser.add_argument("--project-dir", help="target project directory (default: cwd)")
    status_parser.add_argument("--user", action="store_true", help="report on ~/.claude instead of a project")
    status_parser.add_argument("--for-hook", action="store_true", help="report only what's worth interrupting a session for; print nothing when there isn't any")
    status_parser.set_defaults(func=_cmd_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
