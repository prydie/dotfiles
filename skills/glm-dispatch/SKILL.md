---
name: glm-dispatch
description: Hand a coding or analysis task to GLM 5.3 through the opencode CLI — a second model, in a second family, with a very large context window. Use when asked to dispatch/delegate/hand off to GLM or opencode, to get a second opinion or independent pass from another model, to grind through more files or logs than are worth reading directly, or when a long mechanical transformation would otherwise be done by hand.
---

# Dispatching work to GLM 5.3 via opencode

`opencode` is a headless agentic CLI. This machine points it at GLM 5.3 with a
large context window, so it is the cheapest way to get a *second model's*
attempt at a problem without leaving the terminal. Claude Code can host GLM too,
via `bin/claude-glm` — see
[Claude Code as the harness](#claude-code-as-the-harness).

This skill is the dispatch path. For adversarial code review specifically, use
`multi-review` instead — it already runs GLM as one of three engines, with
cross-examination. Dispatch here when you want GLM on a task, not a review.

## Is GLM the right call?

Decide before dispatching. A handoff costs minutes and a round trip; doing it
reflexively is worse than not having the option.

| Task shape | Where it goes |
|---|---|
| Reading far more code/logs/traces than is worth pulling into this context | **GLM** — the context window is the point |
| An independent second attempt after this thread is stuck or looping | **GLM** — a different family fails differently |
| Wide mechanical edits: rename across N files, migrate a call signature, port a pattern | **GLM** — tedious, verifiable, low-judgement |
| A first opinion you will not verify | **Nobody** — dispatch produces claims, not facts |
| Anything needing an *enforced* filesystem/network boundary | **Codex** — its sandbox is OS-level; opencode's is not |
| Small, bounded, already-understood work | **Here** — the handoff costs more than the task |
| Anything touching credentials, or work the user must vouch for | **Here** |

### What it is good at

- **Bulk context.** The window is far larger than is practical to fill by hand.
  Whole-subsystem sweeps, long log and trace analysis, "find every caller of X
  across this monorepo" are its best case.
- **Decorrelated errors.** It is a different model family, so it misses
  different things. That independence is the entire value of a second opinion —
  and the premise `multi-review` is built on. A confirmation from GLM is
  evidence; agreement between two of the same model is not.
- **Grinding.** Long, repetitive, individually-boring transformations where the
  work is mechanical and the result is checkable.
- **Empirical habits.** Observed behaviour on this setup: it runs commands to
  test its own hypotheses rather than asserting from reading, and it checks
  whether a failure predates the change before calling it a regression.

### What to watch

- **"Read-only" is a contract, not a boundary.** With `edit: deny` but bash
  allowed, GLM edited a file anyway on its first attempt — see the overlay
  table below. If the boundary must actually hold, deny bash outright, use
  Codex's OS-level sandbox, or use a container. This is the most important
  limit here.
- **Verify its output.** Same as any model, and more so for an unattended run
  you did not watch. Treat findings as leads to confirm, not conclusions.
- **Long agentic tool-loops** are where any model drifts furthest from intent.
  Prefer one well-scoped task over an open-ended mandate.
- **The evidence base here is thin** — this guidance comes from observed runs on
  this machine, not a broad benchmark. Revise it as you learn more.

## The invocation

```bash
opencode run --auto --pure "<task>" < /dev/null
```

Every element is load-bearing, and **each failure below is silent**:

| Element | Without it |
|---|---|
| `--auto` | Headless has no TTY, so every `"ask"` rule **auto-rejects**. The run dies on its first gated tool call. |
| `--pure` | Plugins in the target tree **execute on your host**. |
| `< /dev/null` | Hangs forever, at near-zero CPU, with no output. Looks alive; is not. |
| `--dir <path>` | Runs against your cwd rather than the tree you meant. |

`--dangerously-skip-permissions` is **not a real flag**. yargs ignores unknown
options silently, so passing it does nothing and the run stays fully gated.
The real flag is `--auto`.

### Useful additions

```bash
--dir /path/to/tree        # run somewhere else
--variant low|high|max     # reasoning effort (this config defines all three)
-m provider/model          # override the model; see `opencode models`
--continue                 # continue the last session
--session <id> --fork      # branch off a specific session
--format json              # raw JSON events, for scripting
--thinking                 # show reasoning blocks
```

## Claude Code as the harness

The same GLM 5.3 is reachable through the Claude Code harness:
`bin/claude-glm` points `claude` at a local LiteLLM proxy that translates the
Anthropic API to the GLM endpoint, with the subscription `claude` left
untouched. Use it when Claude Code is the better harness — its allowed-tools
list is a real boundary, unlike opencode's overlays — or when a Claude Code
session is doing the dispatching.

```bash
claude-glm -p "<task>"                        # print mode; result on stdout
claude-glm -p "<task>" --allowedTools "Read,Glob,Grep"   # read-only GLM run
```

The prompt goes immediately after `-p`: with a flag in between, claude treats
the prompt as that flag's value and dies with "Input must be provided either
through stdin or as a prompt argument". A prompt on stdin works too. The
wrapper also sets `CLAUDE_CODE_AUTO_MODE_SERVER=0`, so an auto-mode session
never holds an action behind the gateway "not eligible" notice nor prints it
to stderr.

With no `Bash` in `--allowedTools`, GLM has no write primitive at all — the
opencode `read-only.json` caveat ("a denylist cannot close the hole; every
shell is a write primitive") does not apply, because there is no shell. For a
write-capable run, prefer a disposable clone or worktree as below, or allow only
the specific tools the task needs. Without `-p`, `claude-glm` opens an
interactive session with the normal permission prompts.

## Write-capable vs read-only — the opposite of Codex

Codex is read-only until you pass `--write`. **opencode is the reverse**: with
`--auto` it will edit, commit, and push unless a permission config denies it.
There is no `--write` flag to withhold.

Two overlays ship beside this skill. `OPENCODE_CONFIG` **merges over** the
personal config rather than replacing it, so providers and API keys are
inherited and an overlay only has to state permissions. Later rules win.

```bash
OPENCODE_CONFIG=~/.dotfiles/skills/glm-dispatch/read-only.json \
  opencode run --auto --pure --dir "$TREE" "<task>" < /dev/null
```

| Overlay | Tools left | Use for |
|---|---|---|
| `read-only.json` | read/glob/grep/webfetch + **bash**, `edit` denied, git/gh mutations denied | Work needing `gh`, `git log`, or the repo's test gates |
| `no-write.json` | read/glob/grep only — bash and webfetch denied too | When the tree must actually survive unchanged |

**`read-only.json` does not make the run read-only.** Measured, on this setup:
given `edit: deny` and a bug to fix, GLM fixed it anyway on its first attempt
with `printf '...' > calc.py`. It was not evading anything — bash was simply the
tool it had. `edit: deny` does work in the narrow sense (the edit tool is not
even offered in the toolset), but a denylist of bash patterns cannot close the
hole; every shell is a write primitive. With `no-write.json` the same prompt
left the file untouched, and the model said so plainly.

So: pick `read-only.json` when you need tooling and can tolerate a *contract*;
pick `no-write.json` when you need a *boundary* and can live without bash. If
you need both tooling and a real boundary, neither overlay is the answer — use
Codex's OS-level sandbox, or run opencode in a container.

One more thing no overlay can do: **project config in the target tree wins over
`OPENCODE_CONFIG`.** An `opencode.json` there can flip `edit: deny` back to
`allow` and inject its own system instructions. Before running against a tree
you do not control, rename `opencode.json`, `opencode.jsonc`, and `.opencode`
out of the way.

For write-capable work, prefer a disposable clone or a worktree you own over the
user's live checkout — and note that a `git worktree` shares `.git/config` with
the real repo, so restricting push in one restricts it in both. A clone is safer.

## Long runs: background it, then `wait`

Runs can take tens of minutes. Background the run and block on its **recorded
PID**:

```bash
opencode run --auto --pure --dir "$TREE" "$PROMPT" > out.md 2> err.txt < /dev/null &
pid=$!
wait "$pid"; rc=$?
echo "exited rc=$rc; out $(wc -c < out.md) bytes"
```

`wait` both blocks and reaps, so zombies cannot strand the loop. Three ways this
goes wrong, all observed live:

- **`pgrep -f 'opencode run …'` matches the watcher itself** — the pattern text
  sits in the watcher's own command line, so the loop never exits. If a pattern
  is truly unavoidable, break the self-match: `'opencode run --auto --pur[e]'`.
- **Iteration caps** (`[ $n -lt 20 ]`) report "still running" and quit early. A
  legitimate run can exceed any cap you pick.
- **`kill -0` succeeds on zombies**, so a PID-liveness loop can spin forever on
  a process that already exited.

Dispatching from a subagent keeps a long run's output out of the main context;
prefer that for anything verbose.

## Before blaming the model

An unresolvable model fails with a generic `Error: Unexpected server error`,
which reads like a backend fault rather than a config one. Check first:

```bash
opencode models          # every model that actually resolves
opencode debug config    # the fully resolved config, after all merging
opencode debug paths     # config / data / state / cache locations
```

A provider only exposes the models it declares, so `provider/some-model` fails
if that provider block does not list it. Endpoints here have moved more than
once — trust `opencode models` over any URL written down, including in this
file. Config lives at `~/.config/opencode/opencode.jsonc` (machine-local, not in
the dotfiles repo) and reads its key from the environment via `~/.zshenv.local`.

## Boundaries

- Report what GLM actually returned. Do not present its claims as verified, and
  do not quietly repair its output to look better than it was.
- Never dispatch secrets, tokens, or credential material in a prompt.
- A dispatched run is still your responsibility: review a write-capable run's
  diff before it reaches a commit.
