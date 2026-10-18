---
name: tauri-feedback-session
description: Collect and act on end-user feedback from a running Tauri app. The user clicks elements in the live window and writes notes (Agentation toolbar); the agent gets them over MCP with the source file:line, sees and drives the window over the WebView2 debugging port, fixes in a fast loop and logs each finding for one verification pass at closure. Use when the user starts or resumes a hands-on testing or user-feedback session on a Tauri app, says they will test by hand, or sends Agentation notes.
---

# Tauri feedback session

Hands-on user testing of the running Tauri app, with fast fix loops: fix
now, verify once at closure. The findings go into a log the project already
keeps — with `project-type-app`, the current plan's findings table — and this
skill is the procedure around it.

Windows only as written: the window is reached through WebView2's debugging
port. The toolbar and the note loop work on any platform.

## One-time setup in the project

Check each piece; set up what is missing, with the user's agreement (it adds
a dependency and a script).

1. **The toolbar, dev builds only.** `npm install -D agentation`, then mount
   it behind `import.meta.env.DEV` in `main.tsx`, so it never reaches a
   release build:
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
2. **The notes server, as an MCP server of the session:**
   `claude mcp add --scope local agentation -- npx -y agentation-mcp server`.
   It only loads at session start: after adding it, the session restarts.
3. **The window driver.** Copy `references/ui.mjs` to `scripts/ui.mjs`. Node
   22 or later, no dependency.
4. **A dev launcher** (`scripts/dev-feedback.ps1` or a switch on an existing
   one) that runs `tauri dev` with
   `$env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = '--remote-debugging-port=9222 --remote-allow-origins=*'`,
   and clears it afterwards. If the app opens user data (a project, a
   config), the launcher points it at a **copy** in `%TEMP%`, never at a
   committed fixture: a dev app rewrites what it opens and dirties git.
   Record the launcher in `AGENTS.md`'s Commands table.

## Start

1. Ask the user to run the dev launcher. The first debug build is slow.
2. Check the link: `curl http://localhost:4747/health` (notes server),
   `node scripts/ui.mjs shot <file>` (window), `agentation_list_sessions`
   (the toolbar registered a session).
3. Name the log that will hold the findings, and the branch it lives on.

## Receive notes

- The user clicks the toolbar's round button, bottom right, then an element
  (or drags a region; `Ctrl/Cmd+click` multi-selects) and writes a note. No
  right click: the toolbar has no context menu.
- Read them with `agentation_get_all_pending`. Each carries the selector,
  nearby text, bounding box, computed styles and the **source file and
  line**. React component names come through only when the toolbar's output
  detail is not `compact`.
- Fallback: the toolbar's "Copy" gives markdown the user can paste.
- Ambiguous note ("in red": text, fill or border?): reply with
  `agentation_reply` or ask in chat before changing anything.
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
  front-end edits; Rust edits rebuild and restart the app.
- Defect or behaviour change, same loop. A change is never silent: the row
  names the spec it departs from, and the plan's decisions record it. Specs,
  requirements and ADRs are reconciled at closure; an ADR it contradicts is
  amended at closure, up to Proposed only.
- A cheap test goes with the fix; otherwise flag the row `needs-test`.
- A genuinely new feature is a question for the user, not a loop item.
- No commit, merge or push without the user's ask.

## Gotchas

- **Space (or any key) does nothing in a note.** The toolbar is a custom
  element with a shadow root: a window-level key handler sees the host, not
  the `textarea`, and a global shortcut swallows the key. Every global key
  handler must test the real target, `event.composedPath()[0]`, before
  acting.
- The round toolbar button overlaps the bottom-right corner of the window
  (often a status bar).
- A note's source line points at the dev build; after a few hot reloads,
  re-read the file rather than trusting the line number.

## Closure

1. The project's full gate.
2. The findings log becomes the verification list: walk it on a release
   build, write the `needs-test` tests.
3. Reconcile specs, requirements and ADRs for the change rows, get a
   fresh-context review of the diff, close the plan.
