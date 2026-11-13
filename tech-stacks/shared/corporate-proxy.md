# Behind the corporate proxy

The proxy re-signs TLS with the company's root certificate and blocks
certificate-revocation checks. Each tool needs one machine-local setting.
**None of them is versioned**: they belong to the machine, and a colleague
outside the network, or CI, must not inherit them.

| Tool | Symptom | Setting |
|---|---|---|
| Cargo | `CRYPT_E_NO_REVOCATION_CHECK` when fetching from crates.io | `[http] check-revoke = false` in `%USERPROFILE%\.cargo\config.toml` (or `CARGO_HTTP_CHECK_REVOKE=false` for one shell). TLS itself is still verified |
| Go | `x509: certificate signed by unknown authority`, or a fetch that times out | On Windows, Go verifies against the system store, where the proxy's root lives, so usually nothing is needed. If the network requires it, `go env -w GOPROXY=<internal proxy>,direct`, and `HTTPS_PROXY` in the user environment. `GOPRIVATE` for private modules only |
| uv (Python) | `invalid peer certificate: UnknownIssuer` when fetching from PyPI or downloading an interpreter | `UV_SYSTEM_CERTS=true` (user environment variable): uv trusts the Windows store instead of its bundled roots. Older uv releases name it `UV_NATIVE_TLS` |
| npm / Node | `UNABLE_TO_GET_ISSUER_CERT_LOCALLY`, `SELF_SIGNED_CERT_IN_CHAIN` | `NODE_OPTIONS=--use-system-ca` (user environment variable): Node trusts the Windows store, where the proxy's root lives. Where that flag is unavailable, export the root as PEM and set `NODE_EXTRA_CA_CERTS` to its path. A project's scripts can set the flag for the session themselves (a dot-sourced `scripts/node-env.ps1`, Node 22.15+ / 23.8+ only), which covers a colleague who never touched the environment; `wails3 dev` reports the failure as a bare exit code, not as the npm error |
| PowerShell | a script is refused by the execution policy | the CurrentUser policy is `RemoteSigned`: run `powershell -NoProfile -File scripts\<name>.ps1`. **Never** `-ExecutionPolicy Bypass` — the EDR flags it |

Never turn TLS verification off (`strict-ssl=false`,
`NODE_TLS_REJECT_UNAUTHORIZED=0`, `http.sslVerify=false`, `GOINSECURE`) to get
past the proxy: it disables the check that the proxy is the one answering. The
same goes for `GOSUMDB=off`, which drops the check that a module is the one
everyone else got.
