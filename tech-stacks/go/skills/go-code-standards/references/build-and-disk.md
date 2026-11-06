# Build configuration and disk

What the build side of a Go module pins, and why it needs less machinery than
Rust's: no linker setting, no build profile and no cap script. The settings go
in files the project already has.

## What gets pinned

| Setting | Where | What it settles |
|---|---|---|
| `go 1.26.0` + `toolchain go1.26.x` | `go.mod` | the minimum language version, and the one compiler this project builds with |
| `ignore ./frontend/node_modules`, `ignore ./build` | `go.mod`, for a Wails app (the first alone for any other module holding a front end) | what `./...` means (below) |
| golangci-lint version | the project README, and CI's install step | one set of findings across machines: a `go tool` dependency would pull the linter's dependency tree into `go.mod`, which upstream advises against |

Move `go` and `toolchain` together, in their own commit. Run `go mod tidy`
after, and read the diff: it is the only place a transitive upgrade shows up.

**`ignore` is not optional when `frontend/` has `node_modules`.** `./...` skips
only `testdata` and directories starting with `.` or `_`, so it walks into
`node_modules`. Packages there do ship Go source: `flatted`, which ESLint
pulls in through its cache, publishes `golang/pkg/flatted/flatted.go` and no
`go.mod`, so `go test ./...` and `golangci-lint run` treat it as a package of
your module. The `ignore` directive (Go 1.25+) is the fix, and it also removes
the cost of walking that tree.

**`build/` is the same problem in a Wails app.** The template generates Go
under `build/ios` and `build/android`, so `golangci-lint` reports on files
nobody wrote. `wails3 build` compiles the root package and doesn't need them in
`./...`.

## Release flags

`-trimpath -ldflags="-s -w"`: no local paths in the binary, no debug tables. A
Wails project gets these, and `-H windowsgui`, from its generated Taskfiles;
don't restate them. A plain module sets them in its build script.

`go test -race` needs cgo, so a C compiler, on Windows. Where there is none,
run it in CI on Linux rather than dropping it.

## Versioned or machine-local

Shared settings are versioned in the project. `go env -w`, which writes to the
user's Go environment file, is for what belongs to one machine only:

- `GOPRIVATE` for the organisation's private modules. It skips both the public
  proxy and the checksum database for those paths, and nothing else;
- `GOPROXY`, when the network requires an internal one. Behind the corporate
  proxy, see `corporate-proxy.md`.

## Disk

There is no `clean.ps1` here, deliberately. Go's build cache lives outside the
project (`go env GOCACHE`) and trims itself of entries unused for a few days,
so nothing like Cargo's `target/` accumulates per project. A cap script would
be machinery with nothing to do.

When the disk is full anyway, in this order, stopping as soon as there is room:

1. `go clean -cache`: costs one slower rebuild.
2. `frontend/node_modules` and `.task/` in projects no longer built; `npm cache
   clean --force`.
3. `go clean -modcache`: the module cache is never trimmed on its own, and the
   next build downloads what it needs.
