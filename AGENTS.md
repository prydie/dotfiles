# AGENTS

## Remote CI

Use `bin/ci-remote` to run a repository's GitHub Actions jobs on a remote box
rather than pushing to GitHub for a verdict, and to run test tiers the local
workstation cannot afford (envtest, race, integration, vulncheck).

```bash
cd <repo>              # any checkout or worktree; uncommitted work is included
ci-remote hosts        # configured boxes -- the tool is the source of truth
ci-remote jobs         # what would run, and which `uses:` steps are skipped
ci-remote run          # every job in parallel; exits non-zero on failure
ci-remote run --job <Job> --host <host>   # one job, streamed
ci-remote run --detach                    # returns a run id in seconds
ci-remote wait <run-id> --fail-fast       # background it; wakes on 1st failure
ci-remote status <run-id>
ci-remote logs <run-id> --job <Job> --tail 0
```

Notes:
- The working tree is rsynced as-is, so there is no need to commit before
  testing. Gitignored paths stay local and are not deleted on the box.
- Every `uses:` step is skipped (checkout, toolchain setup, cache restore). The
  toolchain is the box's, not `ubuntu-latest`'s — read the skipped list the run
  prints, and never report a green run here as proof CI will pass.
- `strategy: matrix` jobs cannot be expanded; send those to GitHub.
- Size the host to the work — `ci-remote hosts` shows each box's job
  concurrency. Run a whole pipeline only on a box provisioned for it.
- Exit codes: 0 passed, 1 a job failed, 2 usage/config error, 3 not finished.
  A mid-run `status` returns 3 — report progress and poll again, don't block.
- All jobs share one host, unlike GitHub's per-job VMs, so `bind: address
  already in use` is a concurrency artifact: re-run that job alone before
  believing it.
- Runs refuse to start on a host low on disk. Reclaim with
  `ci-remote gc --host <name>`; do not delete other people's checkouts or
  scratch directories on a shared box without asking.
- Shared boxes may already be running someone else's work. Check the load
  before launching a full pipeline, and leave the host's `nice` prefix alone.

## Loki via Grafana

`bin/lq` points `logcli` at a Loki reached through a Grafana datasource proxy,
where Grafana is published as a Teleport application. `logcli` does the real
work -- query, tail, labels, series, stats.

```bash
lq apps                               # Grafana apps
lq datasources <app>                  # that app's Loki datasources
eval "$(lq up <app> [datasource-uid])" # exports LOKI_ADDR + client cert/key
logcli query --tail '{namespace="..."}'
lq queries                            # named queries
lq q <name> [args...] [-- logcli-args...]
```

Going through Grafana rather than a port-forward matters for three reasons:

- **It needs no Kubernetes access**, so a viewer role is enough. A port-forward
  needs more, and reading a tenant out of the log shipper's Secret needs more
  still -- which is not granted uniformly across clusters.
- **Grafana's datasource config supplies the Loki tenant**, so there is no
  `X-Scope-OrgID` to get wrong. A wrong tenant does not error: `/labels` still
  returns a full label list, while queries return empty. That is
  indistinguishable from a quiet window.
- **Nothing runs in the background**, so there is nothing to leak or stop.

One deployment usually publishes several Loki datasources -- its own, and often
separate ones for tenant control planes or audit. `lq up` refuses to pick when
there is more than one, because the wrong datasource is another plausible empty
result. `lq datasources` lists them.

`lq q` reports a line count and, on zero, says what still needs confirming
before it can be read as an absence.

Named queries live in `${XDG_CONFIG_HOME:-~/.config}/loki-queries/*.logql` and
are deliberately not tracked here -- templates encode a deployment's own
namespaces and log schema. `config/loki-queries/example.logql.sample` is the
format. Completion offers apps and query names, asked of `lq` at completion
time:

```bash
lq completion zsh > "${XDG_DATA_HOME:-$HOME/.local/share}/zsh/site-functions/_lq"
```

Override app discovery with `LQ_APP_PATTERN` (default `grafana`).

## Visual Review

Use `bin/webshot` to capture webpages for visual inspection.

Authenticated Home Assistant pages should be captured by cloning the local Chrome profile instead of touching the live profile directly:

```bash
bin/webshot \
  --clone-user-data-dir-from ~/.config/google-chrome \
  --profile-directory Default \
  https://hass.nas.prydie.co.uk/solar \
  -o /tmp/ha-solar.png
```

Notes:
- `--clone-user-data-dir-from` is preferred over `--user-data-dir` for an already-open Chrome profile. It avoids `SingletonLock` errors and does not mutate the live profile.
- For Grafana or other HTTP Basic auth pages, prefer `--basic-auth user:password` over embedding credentials in the URL. Some dashboard frontends break when their JavaScript sees `user:pass@host` URLs.
- Use `--profile-directory Default` unless a different Chrome profile is known to hold the logged-in session.
- Default output is under `/tmp`; pass `-o` when you want a stable path.
- Adjust viewport with `--width` and `--height` when reviewing responsive layouts.
- Increase `--timeout-ms` for slower dashboards or cards that need more time to render.

Recommended review loop for Home Assistant dashboards:
1. Apply dashboard config with `uv run bin/ha dashboard set-config ...`
2. Capture the page with `bin/webshot --clone-user-data-dir-from ...`
3. Inspect the resulting image and iterate on layout/content.
