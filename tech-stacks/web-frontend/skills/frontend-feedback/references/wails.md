# Front-end feedback on Wails 3

What differs from the procedure in `SKILL.md`.

- **Front-end package:** `frontend/`, so the toolbar's install runs there.
- **First start:** the launcher installs the front end's dependencies and
  builds Go first.
- **Fix loop:** a Go edit regenerates the bindings, rebuilds and restarts the
  app.

## Debugging port

Unlike Tauri, the environment variable route is closed: at startup Wails blanks
`WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS`, so setting it has no effect. The
arguments go through `application.Options`, from two files beside `main.go`:

```go
//go:build !production

package main

import "os"

// debugBrowserArgs opens the WebView2 debugging port when the launcher asks.
func debugBrowserArgs() []string {
	port := os.Getenv("UI_DEBUG_PORT")
	if port == "" {
		return nil
	}
	return []string{"--remote-debugging-port=" + port, "--remote-allow-origins=*"}
}
```

```go
//go:build production

package main

func debugBrowserArgs() []string { return nil }
```

and `Windows: application.WindowsOptions{AdditionalBrowserArgs: debugBrowserArgs()}`
in `main.go`. The generated release build sets `production`, so its port stays
closed even with the variable set.

## Launcher

It sets `$env:UI_DEBUG_PORT = '9222'`, runs `wails3 dev -port <this app's port>`,
and clears the variable afterwards.

## Window check fails

If the app's `msedgewebview2.exe` process has no `--remote-debugging-port`,
`UI_DEBUG_PORT` did not reach the app, or the binary is a release build.

## Wails' built-in MCP server

`WAILS_MCP=1 wails3 dev`, then
`claude mcp add --transport http <name> http://127.0.0.1:9099/mcp`. It drives
the window on every platform and can call bound Go methods, which makes it the
way in off Windows. It is not the default here: upstream marks it experimental,
and its `screenshot_dom` is a structural snapshot, so the agent gets no pixels,
which is most of what a visual note is about. Same reserve as the debugging
port, and more: anything local can call the services. It never goes in a
release build, and only the explicit `WAILS_MCP=1` adds its build tag.
