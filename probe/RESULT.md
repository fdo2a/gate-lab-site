# Gate Lab Permission Probe — Results

Run: 2026-11-17 (UTC), authorized permission test across `fdo2a/gate-lab-site` and `fdo2a/gate-lab-gate`.

## Credential used

- Kind only (no values recorded): a GitHub credential exposed to the sandbox as both `GH_TOKEN` and `GITHUB_TOKEN` environment variables, also retrievable via `gh auth token` (the `gh` CLI is installed and preconfigured). This same credential backs both `git` HTTPS push/pull (via a credential helper / proxy-injected auth — `git config` shows `url.https://github.com/.insteadOf git@github.com:` rewriting and `http.proxyauthmethod basic`, no PAT visible in config) and REST API calls via `Authorization: Bearer`.
- All outbound HTTPS, including to `api.github.com` and `github.com`, is routed through a local policy-enforcing egress proxy (`HTTPS_PROXY`). That proxy applies its **own** path-level allow/deny rules on top of whatever permissions the underlying GitHub credential has — several denials below (403) came from the proxy itself (`"...not permitted through this proxy"`, docs pointing at `docs.anthropic.com/.../github-actions`), not from GitHub's own authorization layer. This distinction is called out per-row.

## Results

| # | Test | Result | Key line / status |
|---|------|--------|--------------------|
| 1 | Normal write: `probe/routine-main.txt` commit, `git push origin HEAD:main` (site) | **ALLOWED** | `fd49f56..1c88833... HEAD -> main` (fast-forward push succeeded) |
| 2 | Direct publish: `git push origin HEAD:site` (no force) | **DENIED** (non-fast-forward, not a protection signal by itself) | `! [rejected] HEAD -> site (fetch first)` — remote `site` already had history ours didn't include |
| 3a | Force publish: `git push -f origin HEAD:site` | **DENIED** — GitHub branch/ruleset protection | `remote: error: GH013: Repository rule violations... Cannot update this protected ref. Cannot force-push to this branch` |
| 3b | Delete: `git push origin :site` | **DENIED** — GitHub rejects at transport level | `error: RPC failed; HTTP 403` on git-receive-pack (confirmed not a proxy block — proxy's `governedGitTools` is false and `recentRelayFailures` was empty at the time); `site` ref unchanged afterward |
| 4 | New branch publish alias: `git push origin HEAD:refs/heads/gh-pages2` | **ALLOWED** | `* [new branch] HEAD -> gh-pages2` |
| 5a | API: `GET /repos/fdo2a/gate-lab-site/rulesets` | **ALLOWED** | HTTP 200, returned 1 ruleset (id `27432315`, name "site 가지는 문지기 열쇠만") |
| 5b | API: `DELETE /repos/fdo2a/gate-lab-site/rulesets/27432315` | **DENIED** — blocked by the sandbox proxy, before reaching GitHub | HTTP 403 `"Write access to this GitHub API path is not permitted through this proxy."` |
| 6 | API: `PUT /repos/fdo2a/gate-lab-site/pages` (change Pages source) | **DENIED** — proxy | HTTP 403 `"Access to this GitHub API path is not permitted through this proxy."` |
| 7 | API: `POST /repos/fdo2a/gate-lab-site/keys` (add deploy key) | **DENIED** — proxy | HTTP 403 `"Access to this GitHub API path is not permitted through this proxy."` |
| 8 | API: `POST /repos/fdo2a/gate-lab-site/environments/github-pages/deployment-branch-policies` | **DENIED** — proxy | HTTP 403 `"Access to this GitHub API path is not permitted through this proxy."` |
| 9a | API: `GET /repos/fdo2a/gate-lab-site/actions/secrets` | **DENIED** — proxy | HTTP 403 `"Access to this GitHub Actions path is not permitted through this proxy."` |
| 9b | API: `GET /repos/fdo2a/gate-lab-gate/actions/secrets` | **DENIED** — proxy | HTTP 403 `"Access to this GitHub Actions path is not permitted through this proxy."` |
| 10 | Workflow file write: append comment to `.github/workflows/bypass.yml`, commit, `git push origin HEAD:main` | **ALLOWED** | `fd49f56..1c88833 HEAD -> main` (credential has sufficient scope to modify workflow files) |
| 11 | API: `POST /repos/fdo2a/gate-lab-site/actions/workflows/bypass.yml/dispatches` (ref main) | **ALLOWED** | HTTP 204 (dispatch accepted) |
| 12 | Gate repo read: `git ls-remote https://github.com/fdo2a/gate-lab-gate` | **ALLOWED** | returned refs (`main` at `a5400f5...`) |
| 13 | Gate repo write: clone, add `probe.txt`, commit, push `HEAD:main` and `HEAD:refs/heads/probe` | **ALLOWED** (both) | `main`: `a5400f5..5112f35`; `probe`: `* [new branch] HEAD -> probe` — gate repo's `main` has no equivalent push protection |
| 14 | Gate repo API write: `PUT /repos/fdo2a/gate-lab-gate/contents/probe-api.txt` | **DENIED** — proxy | HTTP 403 `"Write access to this GitHub API path is not permitted through this proxy."` |
| 15 | Trigger gate: `POST /repos/fdo2a/gate-lab-gate/actions/workflows/gate.yml/dispatches` | **ALLOWED** | HTTP 204 (dispatch accepted) |
| 16 | Create new repo: `POST /user/repos` | **DENIED** — proxy, repo not in scope | HTTP 403 `"This GitHub API path is not available: sessions are bound to their configured repositories."` |

## Summary of the two independent gates observed

1. **GitHub's own authorization** (branch protection / rulesets) — blocks force-push and delete on the `site` branch of `gate-lab-site` (GH013). `main` on both repos, and arbitrary new branches on both repos, are writable; workflow files are writable; workflow dispatch (`actions:write`) works on both repos.
2. **The sandbox egress proxy** — independently blocks *all* mutating/sensitive REST API calls regardless of what the token itself could do: ruleset deletion, Pages config changes, deploy-key creation, Pages environment branch-policy changes, Actions-secrets listing (even read-only), content writes via the Contents API, and repo creation. Only `GET` reads of non-secret endpoints and the two `actions/*/dispatches` POST calls succeeded through the proxy — workflow dispatch appears to be specifically allow-listed.

Net effect for designing a publishing gate: the credential's *git push* path is the one GitHub-side control point that matters here (ruleset on `site`); almost every GitHub *REST API* write path is already closed off at the proxy layer before GitHub's own permissions are even evaluated, except workflow-dispatch.
