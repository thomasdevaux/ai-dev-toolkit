#!/usr/bin/env python3
"""GitLab tool layer for the gitlab-* Claude Code skills.

A single-file, stdlib-only CLI that wraps `glab api` / `glab api graphql`
behind deterministic subcommands: JSON in, JSON out, dry-run previews, diff
hunk-position validation, and idempotence checks (never guessed, never
duplicated). See ../references/capabilities.md for the full capability
catalog and ../README.md for setup.

Every function used for validation/computation (hunk parsing, position
building, idempotence hashing, diff filtering) is a pure function, called
identically by the CLI dispatch and by tests/ — nothing meaningful lives only
in the argv-parsing path.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

__version__ = "0.2.0"

EXIT_OK = 0
EXIT_GENERIC = 1
EXIT_USAGE = 2
EXIT_AUTH = 3
EXIT_STALE = 4
EXIT_NOT_FOUND = 5

DEFAULT_EXCLUDE_GLOBS = [
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "Cargo.lock", "*.lock",
    "vendor/*", "node_modules/*", "dist/*", "target/*", ".claude/worktrees/*",
    "*.min.js", "*.min.css", "*.map",
]

CLOSES_RE = re.compile(
    r"\b(?:Closes?|Fixes?|Resolves?)\s+#(\d+)", re.IGNORECASE
)


class ToolError(Exception):
    def __init__(self, category: str, message: str, hint: str | None = None,
                 exit_code: int = EXIT_GENERIC):
        super().__init__(message)
        self.category = category
        self.message = message
        self.hint = hint
        self.exit_code = exit_code

    def to_json(self) -> dict:
        out = {"error": self.category, "message": self.message}
        if self.hint:
            out["hint"] = self.hint
        return out


def fail(category: str, message: str, hint: str | None = None,
         exit_code: int = EXIT_GENERIC):
    raise ToolError(category, message, hint, exit_code)


# ---------------------------------------------------------------------------
# Process environment (credentials, console encoding)
# ---------------------------------------------------------------------------

# Only these two keys are ever read from a `.env` file: they are exactly what
# `glab` itself reads from its environment. Anything else in the file (an app's
# own settings) is none of this tool's business.
GLAB_ENV_KEYS = ("GITLAB_HOST", "GITLAB_TOKEN")


def parse_env_file(text: str) -> dict[str, str]:
    """Parse the `KEY=value` lines of a `.env` file, keeping only GLAB_ENV_KEYS.

    Understands `export KEY=...`, `#` comment lines and single/double quotes
    around the value; nothing fancier (no interpolation, no multi-line values).
    """
    found: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, sep, value = line.partition("=")
        key = key.strip()
        if not sep or key not in GLAB_ENV_KEYS:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        found[key] = value
    return found


def load_glab_env(candidates: list[Path] | None = None) -> None:
    """Fill GITLAB_HOST / GITLAB_TOKEN from the first `.env` that has them.

    Never overrides a variable that is already set, so an explicit environment
    (or `glab auth login`'s own config) always wins. The values are only handed
    to the `glab` child process through `os.environ` — never printed or logged.

    Candidates: the `.env` of the checkout this tool lives in (the developer's
    real checkout — a disposable worktree has none, `.env` is gitignored), then
    the current directory's.
    """
    if candidates is None:
        candidates = [Path(__file__).resolve().parents[4] / ".env", Path.cwd() / ".env"]
    for path in candidates:
        try:
            values = parse_env_file(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        for key, value in values.items():
            if value and not os.environ.get(key):
                os.environ[key] = value
        if values:
            return


def force_utf8_streams() -> None:
    """Make stdout/stderr UTF-8 whatever the console code page is.

    On Windows the default is cp1252 when output is piped, and every comment
    body starts with an emoji — printing it would raise UnicodeEncodeError.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------------
# glab transport
# ---------------------------------------------------------------------------

def run_glab(argv: list[str]) -> str:
    """Run a `glab` command, return raw stdout text. Raises ToolError on failure."""
    try:
        proc = subprocess.run(
            ["glab", *argv], capture_output=True, text=True, encoding="utf-8"
        )
    except FileNotFoundError:
        fail("glab_not_found", "the `glab` CLI was not found on PATH",
             hint="install glab or add it to PATH")
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        combined = stderr or (proc.stdout or "").strip()
        if "401" in combined or "invalid_token" in combined or "403" in combined:
            fail("auth", f"glab call failed: {combined}",
                 hint="the token is likely missing, expired, or scoped read_api "
                      "only (api scope is needed for writes)",
                 exit_code=EXIT_AUTH)
        if "404" in combined:
            fail("not_found", f"glab call failed: {combined}",
                 exit_code=EXIT_NOT_FOUND)
        fail("glab_error", f"glab call failed: {combined}")
    return proc.stdout


def glab_api(path: str, method: str = "GET",
             raw_fields: dict | None = None, fields: dict | None = None,
             input_file: str | Path | None = None,
             headers: list[str] | None = None,
             paginate: bool = False, graphql: bool = False) -> Any:
    argv = ["api", "graphql" if graphql else path]
    if method and method != "GET":
        argv += ["-X", method]
    for h in (headers or []):
        argv += ["-H", h]
    for k, v in (raw_fields or {}).items():
        argv += ["-f", f"{k}={v}"]
    for k, v in (fields or {}).items():
        argv += ["-F", f"{k}={v}"]
    if input_file:
        argv += ["--input", str(input_file)]
    if paginate:
        argv += ["--paginate", "--output", "ndjson"]
    text = run_glab(argv)
    if paginate:
        items = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                items.append(json.loads(line))
        return items
    text = text.strip()
    return json.loads(text) if text else None


# ---------------------------------------------------------------------------
# Pure logic: hunk parsing / position building
# ---------------------------------------------------------------------------

HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def compute_hunk_map(diff_text: str) -> list[dict]:
    """Parse a unified diff for one file into a flat list of line records:
    {"old_line": int|None, "new_line": int|None, "kind": "added"|"removed"|"context"}
    in file order, across every hunk.
    """
    lines_out: list[dict] = []
    old_ctr = new_ctr = 0
    in_hunk = False
    for raw_line in diff_text.splitlines():
        header = HUNK_HEADER_RE.match(raw_line)
        if header:
            old_ctr = int(header.group(1))
            new_ctr = int(header.group(2))
            in_hunk = True
            continue
        if not in_hunk:
            continue
        if raw_line.startswith("\\"):
            continue  # "\ No newline at end of file"
        if raw_line.startswith("-"):
            lines_out.append({"old_line": old_ctr, "new_line": None, "kind": "removed"})
            old_ctr += 1
        elif raw_line.startswith("+"):
            lines_out.append({"old_line": None, "new_line": new_ctr, "kind": "added"})
            new_ctr += 1
        else:
            lines_out.append({"old_line": old_ctr, "new_line": new_ctr, "kind": "context"})
            old_ctr += 1
            new_ctr += 1
    return lines_out


def find_hunk_line(hunk_map: list[dict], line: int, side: str) -> dict | None:
    key = "old_line" if side == "old" else "new_line"
    for rec in hunk_map:
        if rec.get(key) == line:
            return rec
    return None


def build_position(hunk_map: list[dict], line: int, side: str,
                    diff_refs: dict, old_path: str, new_path: str) -> dict | None:
    """Build a valid GitLab diff `position` object, or None if the requested
    line is outside every hunk (caller must fall back to a general comment).
    """
    rec = find_hunk_line(hunk_map, line, side)
    if rec is None:
        return None
    position = {
        "position_type": "text",
        "base_sha": diff_refs.get("base_sha"),
        "start_sha": diff_refs.get("start_sha"),
        "head_sha": diff_refs.get("head_sha"),
        "old_path": old_path,
        "new_path": new_path,
    }
    kind = rec["kind"]
    if kind == "added":
        position["new_line"] = rec["new_line"]
    elif kind == "removed":
        position["old_line"] = rec["old_line"]
    else:  # context: both required
        position["old_line"] = rec["old_line"]
        position["new_line"] = rec["new_line"]
    return position


# ---------------------------------------------------------------------------
# Pure logic: diff filtering
# ---------------------------------------------------------------------------

def is_excluded(path: str, exclude_globs: list[str], include_globs: list[str]) -> bool:
    for pat in include_globs:
        if fnmatch.fnmatch(path, pat):
            return False
    for pat in exclude_globs:
        if fnmatch.fnmatch(path, pat):
            return True
    return False


def filter_diff_files(files: list[dict], include_globs: list[str] | None = None) -> dict:
    """files: list of {"old_path", "new_path", "diff", "diff_truncated"?}.
    Returns {"files": [...kept...], "excluded_files": [...], "truncated_files": [...]}.
    """
    include_globs = include_globs or []
    kept, excluded, truncated = [], [], []
    for f in files:
        path = f.get("new_path") or f.get("old_path") or ""
        if is_excluded(path, DEFAULT_EXCLUDE_GLOBS, include_globs):
            excluded.append({"path": path, "reason": "matches default exclude pattern"})
            continue
        if f.get("diff_truncated") or (f.get("diff") == "" and not f.get("new_file")
                                        and not f.get("deleted_file")):
            truncated.append({"path": path, "reason": "diff empty/marked truncated by GitLab"})
        kept.append(f)
    return {"files": kept, "excluded_files": excluded, "truncated_files": truncated}


def parse_closes_issues_from_description(description: str) -> list[int]:
    return sorted({int(m) for m in CLOSES_RE.findall(description or "")})


# ---------------------------------------------------------------------------
# Pure logic: idempotence
# ---------------------------------------------------------------------------

def normalize_body(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def idempotence_hash(kind: str, target: str, body: str) -> str:
    payload = json.dumps(
        {"kind": kind, "target": target, "body_normalized": normalize_body(body)},
        sort_keys=True, ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def build_marked_body(prefix_line: str, body: str, kind: str, target: str) -> tuple[str, str]:
    """Returns (full_body_with_marker, hash)."""
    h = idempotence_hash(kind, target, body)
    full = f"{prefix_line}\n<!-- ai-hash:{h} -->\n\n{body}" if prefix_line else \
           f"{body}\n<!-- ai-hash:{h} -->"
    return full, h


def find_existing_hash(bodies: list[str], target_hash: str) -> bool:
    marker = f"<!-- ai-hash:{target_hash} -->"
    return any(marker in (b or "") for b in bodies)


# ---------------------------------------------------------------------------
# Capabilities: MR
# ---------------------------------------------------------------------------

def mr_get(iid: int) -> dict:
    data = glab_api(f"projects/:id/merge_requests/{iid}")
    return {
        "iid": data["iid"],
        "title": data["title"],
        "description": data.get("description") or "",
        "state": data["state"],
        "source_branch": data["source_branch"],
        "target_branch": data["target_branch"],
        "diff_refs": data.get("diff_refs") or {},
        "web_url": data.get("web_url"),
        "labels": data.get("labels") or [],
    }


def mr_diff_raw(iid: int) -> list[dict]:
    pages = glab_api(f"projects/:id/merge_requests/{iid}/diffs?per_page=100", paginate=True)
    return pages


def cmd_mr_diff(args):
    files = mr_diff_raw(args.iid)
    result = filter_diff_files(files, include_globs=args.include or [])
    out = {
        "files": [
            {"old_path": f.get("old_path"), "new_path": f.get("new_path"), "diff": f.get("diff", "")}
            for f in result["files"]
        ],
        "excluded_files": result["excluded_files"],
        "truncated_files": result["truncated_files"],
    }
    print_json(out)


def cmd_mr_hunks(args):
    files = mr_diff_raw(args.iid)
    match = next((f for f in files if (f.get("new_path") or f.get("old_path")) == args.path), None)
    if match is None:
        fail("not_found", f"path {args.path!r} not found in MR !{args.iid} diff",
             exit_code=EXIT_NOT_FOUND)
    print_json(compute_hunk_map(match.get("diff", "")))


def cmd_mr_get(args):
    print_json(mr_get(args.iid))


def cmd_mr_closes_issues(args):
    try:
        data = glab_api(f"projects/:id/merge_requests/{args.iid}/closes_issues")
    except ToolError as e:
        if e.category == "not_found":
            data = None
        else:
            raise
    if data:
        print_json({"source": "api", "issues": [
            {"iid": i["iid"], "web_url": i.get("web_url")} for i in data
        ]})
        return
    mr = mr_get(args.iid)
    iids = parse_closes_issues_from_description(mr["description"])
    if iids:
        print_json({"source": "description_fallback", "issues": [{"iid": i, "web_url": None} for i in iids]})
    else:
        print_json({"source": "none", "issues": []})


def cmd_mr_discussions(args):
    raw = glab_api(f"projects/:id/merge_requests/{args.iid}/discussions?per_page=100", paginate=True)
    out = []
    for d in raw:
        notes = d.get("notes") or []
        real_notes = [n for n in notes if n.get("resolvable") or n.get("type") == "DiscussionNote"]
        if not real_notes:
            continue  # system note only (e.g. "changed the description")
        resolved = all(n.get("resolved", True) for n in real_notes if n.get("resolvable"))
        if args.unresolved_only and resolved:
            continue
        out.append({
            "discussion_id": d["id"],
            "resolved": resolved,
            "notes": [
                {
                    "id": n["id"], "author": n.get("author", {}).get("username"),
                    "body": n.get("body", ""), "created_at": n.get("created_at"),
                    "position": n.get("position"),
                }
                for n in real_notes
            ],
        })
    print_json(out)


def check_expect_head_sha(iid: int, expect_head_sha: str | None):
    if not expect_head_sha:
        return
    current = mr_get(iid)["diff_refs"].get("head_sha")
    if current != expect_head_sha:
        fail("stale_head_sha",
             f"MR !{iid} head is {current}, expected {expect_head_sha} — it moved since analysis",
             hint="re-fetch the MR and redo before posting", exit_code=EXIT_STALE)


def read_body_file(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def write_temp_json(payload: dict) -> Path:
    import tempfile
    fd, name = tempfile.mkstemp(suffix=".json")
    os.close(fd)  # mkstemp's fd must be closed before the file can be unlinked on Windows
    p = Path(name)
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return p


def existing_note_bodies_for_mr(iid: int) -> list[str]:
    discussions = glab_api(f"projects/:id/merge_requests/{iid}/discussions?per_page=100", paginate=True)
    bodies = []
    for d in discussions:
        for n in d.get("notes") or []:
            bodies.append(n.get("body", ""))
    try:
        drafts = glab_api(f"projects/:id/merge_requests/{iid}/draft_notes")
        for n in drafts or []:
            bodies.append(n.get("note", ""))
    except ToolError:
        pass
    return bodies


def cmd_mr_note_create(args):
    check_expect_head_sha(args.iid, args.expect_head_sha)
    body = read_body_file(args.body_file)
    target = "general"
    full_body, h = build_marked_body("", body, args.kind, target)
    if find_existing_hash(existing_note_bodies_for_mr(args.iid), h):
        print_json({"status": "skipped_duplicate"})
        return
    payload = {"note": full_body}
    if args.dry_run:
        print_json({"status": "dry_run", "would_call": f"POST projects/:id/merge_requests/{args.iid}/draft_notes",
                     "payload": payload, "idempotence_hash": h, "duplicate_found": False})
        return
    tmp = write_temp_json(payload)
    try:
        resp = glab_api(f"projects/:id/merge_requests/{args.iid}/draft_notes", method="POST",
                         input_file=tmp, headers=["Content-Type: application/json"])
    finally:
        tmp.unlink(missing_ok=True)
    print_json({"status": "created", "draft_note_id": resp.get("id")})


def cmd_mr_discussion_create(args):
    check_expect_head_sha(args.iid, args.expect_head_sha)
    body = read_body_file(args.body_file)
    mr = mr_get(args.iid)
    hunk_map = compute_hunk_map(next(
        (f.get("diff", "") for f in mr_diff_raw(args.iid)
         if (f.get("new_path") or f.get("old_path")) == args.path), ""
    ))
    position = build_position(hunk_map, args.line, args.side, mr["diff_refs"], args.path, args.path)
    if position is None:
        fallback_reason = f"line {args.line} ({args.side}) in {args.path} is outside any hunk of the current diff"
        target = "general"
        full_body, h = build_marked_body("", body, args.kind, target)
        if find_existing_hash(existing_note_bodies_for_mr(args.iid), h):
            print_json({"status": "skipped_duplicate"})
            return
        payload = {"note": full_body}
        if args.dry_run:
            print_json({"status": "dry_run", "would_call": f"POST projects/:id/merge_requests/{args.iid}/draft_notes",
                         "payload": payload, "idempotence_hash": h, "duplicate_found": False,
                         "fell_back_general": True, "fallback_reason": fallback_reason})
            return
        tmp = write_temp_json(payload)
        try:
            resp = glab_api(f"projects/:id/merge_requests/{args.iid}/draft_notes", method="POST",
                             input_file=tmp, headers=["Content-Type: application/json"])
        finally:
            tmp.unlink(missing_ok=True)
        print_json({"status": "fell_back_general", "fallback_reason": fallback_reason,
                     "draft_note_id": resp.get("id")})
        return
    target = f"{args.path}:{position.get('new_line') or position.get('old_line')}"
    full_body, h = build_marked_body("", body, args.kind, target)
    if find_existing_hash(existing_note_bodies_for_mr(args.iid), h):
        print_json({"status": "skipped_duplicate"})
        return
    payload = {"note": full_body, "position": position}
    if args.dry_run:
        print_json({"status": "dry_run", "would_call": f"POST projects/:id/merge_requests/{args.iid}/draft_notes",
                     "payload": payload, "idempotence_hash": h, "duplicate_found": False})
        return
    tmp = write_temp_json(payload)
    try:
        resp = glab_api(f"projects/:id/merge_requests/{args.iid}/draft_notes", method="POST",
                         input_file=tmp, headers=["Content-Type: application/json"])
    finally:
        tmp.unlink(missing_ok=True)
    print_json({"status": "created", "position": position, "draft_note_id": resp.get("id")})


def cmd_mr_discussion_reply(args):
    check_expect_head_sha(args.iid, args.expect_head_sha)
    body = read_body_file(args.body_file)
    target = args.discussion_id
    full_body, h = build_marked_body("", body, args.kind, target)
    if find_existing_hash(existing_note_bodies_for_mr(args.iid), h):
        print_json({"status": "skipped_duplicate"})
        return
    payload = {"note": full_body, "in_reply_to_discussion_id": args.discussion_id}
    if args.resolve:
        payload["resolve_discussion"] = True
    if args.dry_run:
        print_json({"status": "dry_run", "would_call": f"POST projects/:id/merge_requests/{args.iid}/draft_notes",
                     "payload": payload, "idempotence_hash": h, "duplicate_found": False})
        return
    tmp = write_temp_json(payload)
    try:
        resp = glab_api(f"projects/:id/merge_requests/{args.iid}/draft_notes", method="POST",
                         input_file=tmp, headers=["Content-Type: application/json"])
    finally:
        tmp.unlink(missing_ok=True)
    print_json({"status": "created", "draft_note_id": resp.get("id")})


def cmd_mr_draft_notes_publish(args):
    if args.dry_run:
        drafts = glab_api(f"projects/:id/merge_requests/{args.iid}/draft_notes")
        print_json({"status": "dry_run", "would_call": f"POST .../merge_requests/{args.iid}/draft_notes/bulk_publish",
                     "pending_count": len(drafts or [])})
        return
    glab_api(f"projects/:id/merge_requests/{args.iid}/draft_notes/bulk_publish", method="POST")
    print_json({"status": "published"})


def cmd_mr_create(args):
    description = Path(args.description_file).read_text(encoding="utf-8") if args.description_file != "-" \
        else sys.stdin.read()
    if args.closes_iid and not re.search(
        rf"\b(?:Closes?|Fixes?|Resolves?)\s+#{args.closes_iid}\b", description, re.IGNORECASE
    ):
        description = f"Closes #{args.closes_iid}\n\n{description}"
    payload = {
        "source_branch": args.source, "target_branch": args.target,
        "title": args.title, "description": description,
        "remove_source_branch": True,
    }
    if args.label:
        payload["labels"] = args.label
    if args.dry_run:
        print_json({"status": "dry_run", "would_call": "POST projects/:id/merge_requests", "payload": payload})
        return
    tmp = write_temp_json(payload)
    try:
        resp = glab_api("projects/:id/merge_requests", method="POST", input_file=tmp,
                         headers=["Content-Type: application/json"])
    finally:
        tmp.unlink(missing_ok=True)
    print_json({"status": "created", "mr_iid": resp.get("iid"), "web_url": resp.get("web_url")})


# ---------------------------------------------------------------------------
# Capabilities: Issue
# ---------------------------------------------------------------------------

HIERARCHY_QUERY = """
query($fullPath: ID!, $iid: String!) {
  project(fullPath: $fullPath) {
    workItems(iids: [$iid]) {
      nodes {
        iid title state workItemType { name } webUrl
        widgets {
          type
          ... on WorkItemWidgetHierarchy {
            hasParent parent { iid title state workItemType { name } webUrl }
            hasChildren children(first: 50) { count nodes { iid title state workItemType { name } webUrl } }
          }
          ... on WorkItemWidgetLinkedItems {
            linkedItems(first: 20) { nodes { linkType workItem { iid title state webUrl } } }
          }
        }
      }
    }
  }
}
""".strip()


def get_project_full_path() -> str:
    # glab has no simple "print full path" command; derive from git remote instead.
    proc = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True)
    remote = proc.stdout.strip()
    m = re.search(r"[:/]([^/:]+(?:/[^/:]+)*?)(?:\.git)?$", remote)
    if not m:
        fail("git_remote", "could not derive the project's full path from `git remote get-url origin`")
    # keep everything after the host (strip user@host: or https://host/)
    path = re.sub(r"^.*?[:/]{1,2}[^/:]+[:/]", "", remote)
    path = path[:-4] if path.endswith(".git") else path
    return path


def fetch_hierarchy(iid: int) -> dict:
    full_path = get_project_full_path()
    payload = {"query": HIERARCHY_QUERY, "variables": {"fullPath": full_path, "iid": str(iid)}}
    tmp = write_temp_json(payload)
    try:
        resp = glab_api("graphql", method="POST", input_file=tmp,
                         headers=["Content-Type: application/json"], graphql=True)
    finally:
        tmp.unlink(missing_ok=True)
    nodes = (((resp or {}).get("data") or {}).get("project") or {}).get("workItems", {}).get("nodes") or []
    if not nodes:
        return {"parent": None, "children": [], "linked_items": [], "caps_hit": []}
    node = nodes[0]
    parent, children, linked = None, [], []
    caps_hit = []
    for widget in node.get("widgets") or []:
        if widget.get("type") == "HIERARCHY":
            if widget.get("hasParent"):
                parent = widget.get("parent")
            child_widget = widget.get("children") or {}
            children = (child_widget.get("nodes") or [])
            if child_widget.get("count", 0) > 50:
                caps_hit.append("children capped at 50")
        elif widget.get("type") == "LINKED_ITEMS":
            linked = [{**(li.get("workItem") or {}), "link_type": li.get("linkType")}
                      for li in (widget.get("linkedItems") or {}).get("nodes") or []]
    return {"parent": parent, "children": children, "linked_items": linked, "caps_hit": caps_hit}


def cmd_issue_get(args):
    data = glab_api(f"projects/:id/issues/{args.iid}")
    out = {
        "iid": data["iid"], "title": data["title"],
        "description": data.get("description") or "",
        "state": data["state"], "labels": data.get("labels") or [],
        "web_url": data.get("web_url"),
    }
    if args.comments:
        notes = glab_api(f"projects/:id/issues/{args.iid}/notes?per_page=100", paginate=True)
        out["notes"] = [
            {"id": n["id"], "author": n.get("author", {}).get("username"),
             "body": n.get("body", ""), "created_at": n.get("created_at"),
             "system": n.get("system", False)}
            for n in notes
        ]
    if args.with_hierarchy:
        try:
            out["hierarchy"] = fetch_hierarchy(args.iid)
        except ToolError as e:
            out["hierarchy"] = None
            out["hierarchy_error"] = e.message
    print_json(out)


def cmd_issue_note_find_marker(args):
    notes = glab_api(f"projects/:id/issues/{args.iid}/notes?per_page=100", paginate=True)
    marker_re = re.compile(re.escape(args.marker) + r"\s+v(\d+)")
    found_note = None
    found_version = None
    for n in sorted(notes, key=lambda n: n.get("created_at", "")):
        m = marker_re.search(n.get("body", ""))
        if m:
            found_note = n
            found_version = int(m.group(1))
    if found_note is None:
        print_json({"found": False})
        return
    later = [n for n in notes if n.get("created_at", "") > found_note.get("created_at", "")
             and n.get("id") != found_note["id"]]
    print_json({
        "found": True, "note_id": found_note["id"], "version": found_version,
        "has_replies_or_reactions": len(later) > 0,
    })


def existing_note_bodies_for_issue(iid: int) -> list[str]:
    notes = glab_api(f"projects/:id/issues/{iid}/notes?per_page=100", paginate=True)
    return [n.get("body", "") for n in notes]


def cmd_issue_note_create(args):
    body = read_body_file(args.body_file)
    target = "general"
    full_body, h = build_marked_body("", body, args.kind, target)
    if find_existing_hash(existing_note_bodies_for_issue(args.iid), h):
        print_json({"status": "skipped_duplicate"})
        return
    if args.dry_run:
        print_json({"status": "dry_run", "would_call": f"POST projects/:id/issues/{args.iid}/notes",
                     "payload": {"body": full_body}, "idempotence_hash": h, "duplicate_found": False})
        return
    tmp = write_temp_text(full_body)
    try:
        resp = glab_api(f"projects/:id/issues/{args.iid}/notes", method="POST",
                         raw_fields={}, fields={"body": f"@{tmp}"})
    finally:
        tmp.unlink(missing_ok=True)
    print_json({"status": "created", "note_id": resp.get("id"), "web_url": resp.get("url")})


def write_temp_text(text: str) -> Path:
    import tempfile
    fd, name = tempfile.mkstemp(suffix=".md")
    os.close(fd)  # mkstemp's fd must be closed before the file can be unlinked on Windows
    p = Path(name)
    p.write_text(text, encoding="utf-8")
    return p


def cmd_issue_note_update(args):
    body = read_body_file(args.body_file)
    target = f"note:{args.note_id}"
    full_body, h = build_marked_body("", body, args.kind, target)
    if args.dry_run:
        print_json({"status": "dry_run",
                     "would_call": f"PUT projects/:id/issues/{args.iid}/notes/{args.note_id}",
                     "payload": {"body": full_body}, "idempotence_hash": h})
        return
    tmp = write_temp_text(full_body)
    try:
        resp = glab_api(f"projects/:id/issues/{args.iid}/notes/{args.note_id}", method="PUT",
                         fields={"body": f"@{tmp}"})
    finally:
        tmp.unlink(missing_ok=True)
    print_json({"status": "updated", "note_id": resp.get("id")})


def cmd_issue_label_set(args):
    if args.dry_run:
        print_json({"status": "dry_run", "would_call": f"PUT projects/:id/issues/{args.iid}",
                     "payload": {"add_labels": args.add}})
        return
    resp = glab_api(f"projects/:id/issues/{args.iid}", method="PUT",
                     fields={"add_labels": args.add})
    print_json({"status": "updated", "labels_after": resp.get("labels")})


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------

def print_json(obj: Any):
    print(json.dumps(obj, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gitlab_tool.py", description=__doc__)
    p.add_argument("--version", action="store_true", help="print version and exit")
    sub = p.add_subparsers(dest="group")

    mr = sub.add_parser("mr")
    mr_sub = mr.add_subparsers(dest="cmd")

    g = mr_sub.add_parser("get")
    g.add_argument("--iid", type=int, required=True)
    g.set_defaults(func=cmd_mr_get)

    g = mr_sub.add_parser("diff")
    g.add_argument("--iid", type=int, required=True)
    g.add_argument("--include", action="append")
    g.set_defaults(func=cmd_mr_diff)

    g = mr_sub.add_parser("hunks")
    g.add_argument("--iid", type=int, required=True)
    g.add_argument("--path", required=True)
    g.set_defaults(func=cmd_mr_hunks)

    g = mr_sub.add_parser("discussions")
    g.add_argument("--iid", type=int, required=True)
    g.add_argument("--unresolved-only", action="store_true")
    g.set_defaults(func=cmd_mr_discussions)

    g = mr_sub.add_parser("closes-issues")
    g.add_argument("--iid", type=int, required=True)
    g.set_defaults(func=cmd_mr_closes_issues)

    note = mr_sub.add_parser("note")
    note_sub = note.add_subparsers(dest="subcmd")
    g = note_sub.add_parser("create")
    g.add_argument("--iid", type=int, required=True)
    g.add_argument("--kind", required=True, choices=["review", "feedback", "plan", "implementation"])
    g.add_argument("--body-file", required=True)
    g.add_argument("--expect-head-sha")
    g.add_argument("--dry-run", action="store_true")
    g.set_defaults(func=cmd_mr_note_create)

    disc = mr_sub.add_parser("discussion")
    disc_sub = disc.add_subparsers(dest="subcmd")
    g = disc_sub.add_parser("create")
    g.add_argument("--iid", type=int, required=True)
    g.add_argument("--kind", required=True, choices=["review", "feedback", "plan", "implementation"])
    g.add_argument("--path", required=True)
    g.add_argument("--line", type=int, required=True)
    g.add_argument("--side", required=True, choices=["old", "new"])
    g.add_argument("--body-file", required=True)
    g.add_argument("--expect-head-sha")
    g.add_argument("--dry-run", action="store_true")
    g.set_defaults(func=cmd_mr_discussion_create)

    g = disc_sub.add_parser("reply")
    g.add_argument("--iid", type=int, required=True)
    g.add_argument("--kind", required=True, choices=["review", "feedback", "plan", "implementation"])
    g.add_argument("--discussion-id", required=True)
    g.add_argument("--body-file", required=True)
    g.add_argument("--resolve", action="store_true")
    g.add_argument("--expect-head-sha")
    g.add_argument("--dry-run", action="store_true")
    g.set_defaults(func=cmd_mr_discussion_reply)

    draft = mr_sub.add_parser("draft-notes")
    draft_sub = draft.add_subparsers(dest="subcmd")
    g = draft_sub.add_parser("publish")
    g.add_argument("--iid", type=int, required=True)
    g.add_argument("--dry-run", action="store_true")
    g.set_defaults(func=cmd_mr_draft_notes_publish)

    g = mr_sub.add_parser("create")
    g.add_argument("--title", required=True)
    g.add_argument("--source", required=True)
    g.add_argument("--target", required=True)
    g.add_argument("--description-file", required=True)
    g.add_argument("--label")
    g.add_argument("--closes-iid", type=int)
    g.add_argument("--dry-run", action="store_true")
    g.set_defaults(func=cmd_mr_create)

    issue = sub.add_parser("issue")
    issue_sub = issue.add_subparsers(dest="cmd")

    g = issue_sub.add_parser("get")
    g.add_argument("--iid", type=int, required=True)
    g.add_argument("--with-hierarchy", action="store_true")
    g.add_argument("--comments", action="store_true")
    g.set_defaults(func=cmd_issue_get)

    inote = issue_sub.add_parser("note")
    inote_sub = inote.add_subparsers(dest="subcmd")
    g = inote_sub.add_parser("create")
    g.add_argument("--iid", type=int, required=True)
    g.add_argument("--kind", required=True, choices=["review", "feedback", "plan", "implementation"])
    g.add_argument("--body-file", required=True)
    g.add_argument("--dry-run", action="store_true")
    g.set_defaults(func=cmd_issue_note_create)

    g = inote_sub.add_parser("update")
    g.add_argument("--iid", type=int, required=True)
    g.add_argument("--kind", required=True, choices=["review", "feedback", "plan", "implementation"])
    g.add_argument("--note-id", required=True)
    g.add_argument("--body-file", required=True)
    g.add_argument("--dry-run", action="store_true")
    g.set_defaults(func=cmd_issue_note_update)

    g = inote_sub.add_parser("find-marker")
    g.add_argument("--iid", type=int, required=True)
    g.add_argument("--marker", required=True)
    g.set_defaults(func=cmd_issue_note_find_marker)

    label = issue_sub.add_parser("label")
    label_sub = label.add_subparsers(dest="subcmd")
    g = label_sub.add_parser("set")
    g.add_argument("--iid", type=int, required=True)
    g.add_argument("--add", required=True)
    g.add_argument("--dry-run", action="store_true")
    g.set_defaults(func=cmd_issue_label_set)

    return p


def main(argv: list[str] | None = None) -> int:
    force_utf8_streams()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"gitlab-common-tools {__version__}")
        return EXIT_OK
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return EXIT_USAGE
    load_glab_env()
    try:
        func(args)
        return EXIT_OK
    except ToolError as e:
        print(json.dumps(e.to_json(), ensure_ascii=False), file=sys.stderr)
        return e.exit_code


if __name__ == "__main__":
    sys.exit(main())
