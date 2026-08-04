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
