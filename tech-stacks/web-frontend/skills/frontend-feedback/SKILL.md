---
name: frontend-feedback
description: Collect and act on end-user feedback from a running front end (Tauri and Wails today, one reference per stack). The user writes notes on elements of the live window (Agentation); the agent gets them with the source file:line, drives the window over its debugging port, fixes fast and logs each finding for one verification at closure. Use when the user starts or resumes a hands-on testing or feedback session on a running app, says they will test by hand, or sends Agentation notes.
---

# Front-end feedback

Hands-on user testing of the running app, with fast fix loops: fix now, verify
once at closure. Every finding goes into one log (see "Findings log"), and this
skill is the procedure around it.

## Find the stack

This file is the procedure; what differs per stack is in one reference. Read
it before anything else:

| The project has | Read |
|---|---|
| `src-tauri/` | `references/tauri.md` |
| `github.com/wailsapp/wails/v3` in `go.mod` | `references/wails.md` |

No match: say so before setting anything up. The note loop works on any React
front end, but the session has no way to see the window until the stack has a
reference (see "Adding a stack").

Both stacks above reach the window through WebView2's debugging port, so they
are Windows only as written. The toolbar and the note loop work on any
platform.

## One-time setup in the project

Check each piece; set up what is missing, with the user's agreement (it adds
a dependency and a script).

1. **The toolbar, dev builds only.** In the front-end package,
   `npm install -D agentation`, then mount it behind `import.meta.env.DEV` in
   `main.tsx`, so it never reaches a release build:
   ```tsx
   const Feedback = import.meta.env.DEV
     ? lazy(async () => {
         const { Agentation } = await import("agentation");
         return { default: () => <Agentation endpoint="http://localhost:4747" /> };
       })
     : null;
   // render {Feedback ? <Suspense fallback={null}><Feedback /></Suspense> : null}
   ```
   Its licence is PolyForm Shield 1.0.0 — not open source. Fine for a dev-only
   dependency of an internal tool that never ships it; say so to the user
   before adding it.
2. **The notes server, as an MCP server of the session.** From the project's
   directory, since local scope belongs to it:
   `claude mcp add --scope local agentation -- npx -y agentation-mcp server`.
   It only loads at session start: after adding it, the session restarts.
   Both steps fetch from the npm registry: behind the corporate proxy they
   fail with `UNABLE_TO_GET_ISSUER_CERT_LOCALLY` until Node trusts the OS
   store (`frontend-code-standards/references/corporate-proxy.md`).
3. **The window driver.** Copy `references/ui.mjs` to `scripts/ui.mjs`. Node
   22 or later, no dependency.
4. **The debugging port and the dev launcher**, as the stack's reference
   describes. The launcher is `scripts/dev-feedback.ps1` or a switch on an
   existing one. If the app opens user data (a project, a config), it points
   the app at a **copy** in `%TEMP%`, never at a committed fixture: a dev app
   rewrites what it opens and dirties git. Record it in `AGENTS.md`'s Commands
   table.

## Start

1. Get the dev launcher running: the user in a separate terminal, or the agent
   as a background process with the user's agreement. The first start builds
   the backend, so it takes a moment.
2. Check the link: `curl http://localhost:4747/health` (notes server),
   `node scripts/ui.mjs shot <file>` (window), `agentation_list_sessions`
   (the toolbar registered a session). If the window check fails, the stack's
   reference says what to look at.
3. Note the session whose URL is this app's dev URL, which its dev port
   identifies. **The notes server is shared**: it listens on port 4747 for every
   project, so the list can hold sessions from other apps.
4. Name the log that will hold the findings, and the branch it lives on.

## Receive notes

- The user clicks the toolbar's round button, bottom right, then an element
  (or drags a region; `Ctrl/Cmd+click` multi-selects) and writes a note. No
  right click: the toolbar has no context menu.
- Read them with `agentation_get_pending` on this app's session, not
  `agentation_get_all_pending`, which also returns other projects' notes. Each
  carries the selector, nearby text, bounding box, computed styles and the
  **source file and line**. React component names depend on the toolbar's
  output detail setting and can be null.
- Fallback: the toolbar's "Copy" gives markdown the user can paste.
- Ambiguous note ("in red": text, fill or border?), or one that landed on a
  container when it talks about what's inside: reply with `agentation_reply`
  or ask in chat before changing anything.
- After handling: `agentation_resolve` with a one-line summary, or
  `agentation_dismiss` with the reason.

## See and drive the window

`node scripts/ui.mjs shot [file] | text | dom [selector] | eval "<js>" |
click "<selector>" | logs [ms] | targets` (port 9222, `UI_DEBUG_PORT` to
change). Save screenshots in the scratchpad and read them. The port exposes
the whole window on localhost: not while confidential data is open in the
app.

## Fix loop

- Per finding: read the code at the given source line, fix, run the
  project's inner-loop check on what changed, add a row to the findings log.
  No full gate and no per-fix manual verification. Vite hot-reloads
  front-end edits, except files under `public/`, which need
  `node scripts/ui.mjs eval "location.reload()"`; backend edits rebuild and
  restart the app.
- Defect or behaviour change, same loop. A change is never silent: the row
  names the spec it departs from, and the log's decisions record it. Specs,
  requirements and ADRs, where the project has them, are reconciled at closure;
  an ADR it contradicts is amended at closure, up to Proposed only.
- A cheap test goes with the fix; otherwise flag the row `needs-test`.
- A genuinely new feature is a question for the user, not a loop item.
- No commit, merge or push without the user's ask.

## Findings log

A file in the project: an existing plan or log if it keeps one, otherwise
`docs/feedback/<YYYY-MM-DD>.md`, whatever the project type.

```markdown
# Feedback session <YYYY-MM-DD>

Branch: <branch>. Dev URL: <url>.

## Findings

| # | Note | Source | Change | Spec departed from | needs-test |
|---|------|--------|--------|--------------------|------------|

## Decisions

- #<n>: <behaviour change, and who confirmed it>
```

## Gotchas

- **The session stopped answering?** Check the launcher first. Closing the
  window ends it with exit code 0, without any error, so everything looks down
  until it is started again.
- **Space (or any key) does nothing in a note.** The toolbar is a custom
  element with a shadow root: a window-level key handler sees the host, not
  the `textarea`, and a global shortcut swallows the key. Every global key
  handler must test the real target, `event.composedPath()[0]`, before
  acting.
- The round toolbar button overlaps the bottom-right corner of the window
  (often a status bar).
- A note's source line points at the dev build; after a few hot reloads,
  re-read the file rather than trusting the line number.
- A backend restart reloads the page and drops unsaved React state. To check a
  long flow after a backend fix, start the flow again rather than reading a
  screen that no longer holds what the note described.

## Closure

1. The project's full gate.
2. The findings log becomes the verification list: walk it on a release
   build, write the `needs-test` tests.
3. Reconcile specs, requirements and ADRs for the change rows, where the
   project has them, get a fresh-context review of the diff, and mark the log
   closed.

## Adding a stack

Add `references/<stack>.md`, and a row to the table in "Find the stack" with
the marker that identifies it. The reference answers only what differs:

- where the front-end package is;
- how the debugging port opens in a dev build, and why it stays closed in a
  release build;
- what the launcher runs;
- what to check when the window check fails;
- anything the stack adds or changes in the loop.

`ui.mjs` speaks the Chrome DevTools Protocol, so any Chromium-based window
works with it unchanged. A stack with another engine needs its own driver,
with the same commands.
