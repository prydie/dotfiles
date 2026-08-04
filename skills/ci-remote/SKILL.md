---
name: ci-remote
description: Run a repository's GitHub Actions CI jobs on a remote Linux box instead of pushing to GitHub. Use when asked to run CI, reproduce a CI failure, check a branch is green before pushing, or run heavy test tiers (envtest, race, integration, vulncheck) that are too slow or too large for the local machine.
---

# Running CI on a remote box

`ci-remote` syncs the current working tree to a remote host and runs the jobs
from a GitHub Actions workflow there. It is repo-agnostic: the job list is read
from the workflow file, so it tracks CI without a per-repo config, and it writes
nothing into the repository under test.

Use it to get a CI verdict in minutes on a big box rather than waiting on a
push, and to run tiers the local workstation cannot afford.

## The loop

```bash
cd <repo>                      # any checkout or worktree
ci-remote jobs                 # what would run, and what is skipped
ci-remote run                  # every job; blocks and reports
ci-remote run --job Unit       # one job; streams live output
ci-remote run --detach         # returns a run id straight away
ci-remote status <run-id>      # job states
ci-remote logs <run-id> --job Unit --tail 0   # full log
ci-remote cancel <run-id>      # stop a run, free the workspace
```

`jobs` and `hosts` are answered locally — no SSH, no `--host` flag, instant.
Call them freely before committing to a run.

With no `--job`, jobs run in parallel up to the host's slot count and `needs:`
ordering is honoured.

## Exit codes — branch on these, not on log text

| Code | Meaning |
|---|---|
| 0 | Every blocking job passed |
| 1 | At least one blocking job failed |
| 2 | Usage or config error (bad job name, unknown run id, host low on disk) |
| 3 | Run has not finished — **no verdict yet** |

Job states in `status`: `PEND` (not launched), `QUEUE` (launched, waiting on a
host slot or an exclusive lock), `RUN`, `PASS`, `FAIL`, `FAIL(advisory)`.
Elapsed time for `RUN` and finished jobs is work only — queue time is separate.

A job is cancelled at its workflow's `timeout-minutes` (the host sets a default
where the workflow gives none), so an abandoned job cannot hold a slot and a
workspace forever.

Code 2 means *you* got something wrong and can retry differently; code 1 is a
genuine CI signal. Code 3 comes from polling `status` mid-run: treat it as "ask
again later", never as success.

## Watching a long run without blocking

The pattern that fits an agent: launch detached, then background a `wait` that
returns early on failure.

```bash
ci-remote run --detach                 # returns in seconds with a run id
ci-remote wait <run-id> --fail-fast    # run this in the background
```

`--detach` returns once the tree is synced and the run is launched — seconds,
not the length of the run, though the first sync of a large repo dominates it.
It is not instant; a ten-second return is normal and is not a hang.

`--fail-fast` returns on the **first** blocking job failure instead of sitting
through the slowest tier, so a lint failure at 30s wakes you at 30s rather than
ten minutes later. Without it, `wait` returns only when everything is done.
Other jobs keep running after a fail-fast return; `ci-remote cancel <run-id>`
stops them and frees the checkout's workspace for the next run.

`status` also accepts `--wait`, `--fail-fast` and `--logs`, so a poll, a block
and a failure-log dump can be collapsed into one call when that suits.

### If someone is waiting on the result

**Poll and report; do not go silent.** A backgrounded `wait` is a convenience,
not your reporting channel: call `status` yourself at each check-in and say how
many jobs are done, which are outstanding, and whether anything has failed. A
run can take ten minutes or more, and parking on a notification with nothing
said in the meantime reads as a stall. `status` is one cheap non-blocking call
and exits 3 while a run is in flight — that is your cue to report progress and
come back, not to block.

## What it does and does not reproduce

It executes the workflow's `run:` steps with GitHub's shell semantics
(`bash --noprofile --norc -eo pipefail`), honouring workflow/job `env`,
`working-directory` and `continue-on-error`, and sets `CI=true`.

It **skips every `uses:` step** — `actions/checkout`, `setup-go`, cache
restores. Those are listed before each run; read that list. Consequences:

- The toolchain is the **box's**, not `ubuntu-latest`'s. A failure caused by a
  version difference will not reproduce, and a pass here does not prove a pass
  on GitHub.
- Caches are the box's own, warm across runs. Expect it to be faster than CI.
- A job whose real work lives in an action (image build, artifact upload) has
  nothing left to run. `ci-remote jobs` shows that as "no runnable steps".

A `strategy: matrix` cannot be expanded, and `if:` conditions are not
evaluated — both are reported as warnings, and matrixed jobs must go to GitHub.

**One host, one network.** GitHub runs each job on its own VM; here they share
the box's network namespace. Jobs that bind fixed or weakly-randomised ports —
envtest, anything standing up a control plane or test server — can therefore
collide when run concurrently, which they never would on GitHub:

```
bind: address already in use
```

That is a **concurrency artifact, not a code failure**. Re-run the affected job
on its own (`ci-remote run --job Envtest`) to get a real verdict, and only
believe the failure if it reproduces alone. Filesystem state is not the issue —
each job gets its own tree.

A host can list such jobs as `exclusive_jobs`, which serialises them against
each other while everything else stays parallel; `ci-remote hosts` shows
whether that is configured. A job held there reports `QUEUE`, not `RUN`, so
waiting time is never mistaken for work.

Job concurrency is also capped host-wide by `max_jobs` across every
invocation — `parallel` alone bounds only your own run, so several agents
launching at once would otherwise oversubscribe the box.

## Code shipping

The **working tree is rsynced, uncommitted changes included** — what runs is
what you have on disk, so there is no need to commit to test. Ignored paths are
skipped using git's own answer, so re-inclusion patterns (`!/.claude/skills/`)
are honoured.

`.git` is included, which is what lets targets like `verify-generate` or a
copyright check diff against the index. **Linked worktrees work**: their `.git`
is a pointer file naming a path that only exists locally, so a standalone `.git`
is assembled on the box instead.

The workspace is per-checkout and persistent, so a re-sync of an unchanged tree
moves a few hundred KB, not the whole checkout.

## Parallel agents

Workspaces are keyed by the absolute path of the local checkout, so agents in
different worktrees never share one and need no coordination. Two runs from the
**same** checkout are a genuine conflict, and the second is refused naming the
run that holds it — wait for that run, or `cancel` it.

Two overrides exist and they are **not** interchangeable: `--force` starts
despite low disk, while `--take-workspace` seizes a workspace from a run
believed dead. Using the latter on a run that is actually alive corrupts the
tree it is building in, so prefer `cancel`.

## Hosts

`ci-remote hosts` lists them and is the source of truth. `--host <name>` picks
one on `run`, `gc` and `cancel` — but **not** on `jobs` or `hosts`, which are
answered locally and take no host. Each entry carries the host's PATH prelude
(non-interactive SSH loads no profile), job concurrency, scheduling policy and
cache variables.

Size the host to the work: run a full pipeline only on a box whose configured
concurrency says it is meant for one; elsewhere prefer a single `--job`. A
shared box may already be running someone else's work — check the load first,
and leave the host's `nice` prefix in place.

## Reading a failure

`run` and `wait` tail the failing jobs' logs automatically. Each step is
delimited:

```
===== step 2/5 Lint =====
...output...
===== step 2/5 Lint -> rc=1 (12s) =====
```

A job stops at its first failing blocking step, so the last delimiter is the
failure. Advisory (`continue-on-error`) steps report `rc` but do not fail the
job, and show as `FAIL(advisory)`.

**Only the `rc=` delimiters and the summary are authoritative.** Passing jobs
routinely contain scary-looking stderr — `fatal:`, `error`, warnings from tools
that are allowed to fail — so never grep log text to decide pass/fail.

## Distinguishing a broken box from broken code

A `FAIL` looks identical whether your code is wrong or the host is unhealthy.
The strongest signal is **several unrelated tiers failing at once**: a real code
defect usually breaks one thing, while a sick box breaks whatever it touches.

- Resource exhaustion reads as an ordinary test failure. Errors like
  `no space left on device`, or a service that times out starting rather than
  asserting something wrong, point at the **host**, not your change.
- Runs are refused up front when either the workspace filesystem or the
  configured scratch filesystem is low. They are usually different devices, so
  checking one proves nothing about the other.
- A pipeline finishing far faster than usual is a red flag, not a win — heavy
  tiers probably aborted early.

When you suspect the host, say so rather than reporting a code failure, and
check with the box's owner before changing anything on it.

Say which host a result came from when reporting it, and never present a green
run here as proof that GitHub CI will pass.

## Housekeeping

The tool prunes after itself: finished runs beyond the host's `keep_runs`, and
workspaces unused past `workspace_ttl_days`. In-flight runs are never removed
and every removal prints. `ci-remote gc --host <name>` applies the same policy
on demand and reports usage.

Never delete another agent's or user's checkouts or scratch directories on a
shared box to make room — ask.
