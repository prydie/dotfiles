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
- Exit codes: 0 passed, 1 a job failed, 2 tool/config error, 3 not finished.
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

### Structured metadata is invisible to `logcli labels`

An OTLP collector's resource attributes do not become Loki labels. Loki 3 keeps
them as *structured metadata*, which `logcli labels` and `logcli series` never
show -- so a datasource can look like it carries no correlating identifier when
it carries several. They filter with a `|` expression after the stream
selector, and need no `| json`:

```bash
logcli query '{service_name="..."} | someResourceAttribute="..."'
```

Check the collector's `resource` processors before concluding a correlation is
missing and building a join to replace it.

One deployment usually publishes several Loki datasources -- its own, and often
separate ones for tenant control planes or audit. `lq up` refuses to pick when
there is more than one, because the wrong datasource is another plausible empty
result. `lq datasources` lists them.

`lq q` reports a line count and, on zero, says what still needs confirming
before it can be read as an absence. A query can also be bound to one
datasource with `<name> @<uid> | <logql>`; running it against a different one
is refused, because a stream selector that exists in only one datasource
returns empty elsewhere rather than erroring.

### Reading the output with hl

`lq q` defaults to `logcli --output=raw`, so each line is the log record itself
with no timestamp or label prefix. That is what any downstream JSON reader
needs, `hl` included, and it pipes straight through:

```bash
lq q errors | hl -P
```

`hl` picks up the timestamp, level, logger and message from the usual JSON
keys with no configuration. What spoils it is the fields a structured logger
repeats on every single line -- build metadata and stack traces -- which crowd
out the part that differs. Hide them, one `-h` per key (a comma-separated list
is silently ignored):

```bash
lq q errors | hl -P -h application -h version -h revision -h stacktrace
```

There is no `HL_HIDE` environment variable, but `HL_CONFIG` points at a file
that can carry the list under `fields.hide`, so the set can live in
`~/.config/hl/` rather than in the shell history. Which keys are noise is a
property of the logger, so that file is not tracked here.

Pass `--output=default` through to `lq q` to get logcli's own timestamp and
label prefix back.

Named queries live in `${XDG_CONFIG_HOME:-~/.config}/loki-queries/*.logql` and
are deliberately not tracked here -- templates encode a deployment's own
namespaces and log schema. `config/loki-queries/example.logql.sample` is the
format. Completion offers apps and query names, asked of `lq` at completion
time:

```bash
lq completion zsh > "${XDG_DATA_HOME:-$HOME/.local/share}/zsh/site-functions/_lq"
```

Override app discovery with `LQ_APP_PATTERN` (default `grafana`).

## GLM via Claude Code (claude-glm)

`bin/claude-glm` runs Claude Code with GLM 5.3 as the model, through the local
LiteLLM proxy (systemd user unit `litellm`, 127.0.0.1:4000, started on demand).
The regular `claude` command keeps using the Anthropic subscription; every
override is scoped to the wrapper's process.

```bash
claude-glm                                        # interactive session on GLM
claude-glm -p "<task>" --allowedTools "Read,Glob,Grep"   # read-only dispatch
```

With no `Bash` in `--allowedTools`, GLM has no write primitive at all — a real
boundary, unlike opencode's permission overlays. The proxy config and its env
file are machine-local in `~/.config/litellm/` (the endpoint names internal
infrastructure; only `*.example` shapes are tracked). One Claude Code process
speaks to one provider: to combine models, dispatch `claude-glm -p` from the
subscription session rather than trying to mix providers inside one process.
The `glm-dispatch` skill covers when to dispatch and how to babysit long runs.

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
