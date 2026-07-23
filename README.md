# Andrew Pryde's dotfiles

Personal dotfiles managed with [`rcm`](https://github.com/thoughtbot/rcm).

## Scope

This repo contains shell/editor/tmux/git config and optional host bootstrap hooks.

- Safe default: `make up` only links dotfiles.
- Opt-in setup: choose a `PROFILE` to install packages/plugins/tools.

## Requirements

- Linux (Debian/Ubuntu recommended for bootstrap scripts)
- `git`, `make`, `rcm` (`install.sh` bootstraps these on Debian/Ubuntu)
- `uv` (installed automatically during package setup)

## Quick start

One-line bootstrap (fresh Ubuntu):

```bash
sudo apt-get update && sudo apt-get install -y git make && git clone https://github.com/prydie/dotfiles.git ~/.dotfiles && cd ~/.dotfiles && make bootstrap PROFILE=full
```

If you prefer SSH auth (recommended when you will push changes):

```bash
sudo apt-get update && sudo apt-get install -y git make && git clone git@github.com:prydie/dotfiles.git ~/.dotfiles && cd ~/.dotfiles && make bootstrap PROFILE=full
```

If the repo is already cloned:

```bash
./install.sh
```

Or manually:

```bash
make up
```

## Common commands

```bash
make help
make up
make bootstrap
make setup
make codex-sandbox-fix
make codex-superpowers
make ai-skills
make tmux-plugins
make agent-session-hooks
make tla-tools
make verify-tla-tools
make ghostty
make ghostty-terminfo
make bruno
make refresh-dev
make gnome-prefs-save
make gnome-prefs-apply
make restic-backup-now
make restic-systemd-enable
make patching
make patching-full
```

## Codex instructions

This repo manages only the public-safe global Codex guidance file:

- `codex/AGENTS.md` links to `~/.codex/AGENTS.md`

The rest of `~/.codex` is intentionally local and untracked because it can
contain auth state, logs, history, caches, memories, per-repo trust settings, and
other private or machine-specific data. Keep private host-specific guidance in
`~/.codex/AGENTS.override.md`.

The repo-root `AGENTS.md` is project guidance for this dotfiles repo only and is
excluded from `rcm` linking so it is not installed as `~/.AGENTS.md`.

`make setup PROFILE=dev|full` installs Codex CLI and attempts to enable the
curated `superpowers@openai-curated` plugin in local `~/.codex` state. Plugin
setup is optional during bootstrap so a Codex/plugin issue does not block the
rest of the machine setup. To refresh or install only that plugin, run:

```bash
make codex-superpowers
```

Generated Codex plugin cache/config remains local to `~/.codex` and is not
tracked by this public repo. Superpowers scratch state under `.superpowers/` is
also ignored; deliberate specs/plans under `docs/superpowers/` remain visible to
Git review.

## Agent skills (mattpocock/skills pilot)

A conservative pilot subset of [`mattpocock/skills`](https://github.com/mattpocock/skills)
is installed globally for both Claude Code and Codex via the
[skills.sh](https://skills.sh/) installer:

```bash
make ai-skills
```

The pilot deliberately excludes the skills that require Matt's
`/setup-matt-pocock-skills` workflow (issue tracker, triage labels, doc layout) —
`ask-matt`, `code-review`, `to-spec`, `to-tickets`, `triage`, `wayfinder`,
`implement`, and `improve-codebase-architecture`. Every skill in the pilot is
self-contained and low blast radius. The subset is the single source of truth in
the `AI_SKILLS` array in [hooks/os](hooks/os):

- `grill-me`, `grilling`, `grill-with-docs` — relentless alignment interviews;
  `grill-with-docs` also uses `domain-modeling` to build ADRs and a glossary.
- `domain-modeling` — maintain a project's `CONTEXT.md` and ADRs.
- `diagnosing-bugs` — structured reproduce → minimise → hypothesise → fix loop.
- `resolving-merge-conflicts` — resolve in-progress conflicts by intent.
- `codebase-design` — deep-module design vocabulary (advisory).
- `writing-great-skills` — reference for authoring skills.
- `prototype`, `handoff`, `tdd`, `research` — design spikes, conversation
  handoff, red-green-refactor, and cited investigation.

`skills.sh` installs the skills into the shared `~/.agents/skills` store and
symlinks them into `~/.claude/skills` for Claude Code. It marks Codex a
"universal" agent and does not populate `~/.codex/skills`, but `codex-cli`
discovers global skills under `${CODEX_HOME:-~/.codex}/skills`, so `make ai-skills`
also symlinks each skill there. The installed skills live outside this repo and
are not tracked; the install is not version-pinned by design — refresh with
`skills update -g`, and remove with `skills remove -g -a claude-code codex -s <name>`.

## Tmux agent checkpoints

`agent-sessions` combines tmux-resurrect's terminal layout with the native
Codex and Claude session IDs. It does not capture pane contents or copy agent
transcripts. It stores private checkpoint manifests under
`${XDG_STATE_HOME:-~/.local/state}/agent-sessions` with mode `0600`.
The Resurrect post-save hook restricts its state directory to `0700` and its
snapshots to `0600`.
Codex panes attached to an app-server retain their `--remote` endpoint instead
of reopening the thread through a standalone local process. Confirmed restore
starts the managed Codex daemon before launching any panes that use its control
socket; a daemon startup failure prevents every agent launch.

Install the plugin and additive user-level lifecycle hooks:

```bash
make tmux-plugins
make agent-session-hooks
```

`PROFILE=dev|full` installs the hooks automatically. The installer preserves
other settings and backs up a settings file before changing it. Restart Codex,
open `/hooks`, and trust the new user hook; an organization policy may disable
user hooks.

Before rebooting:

```bash
agent-sessions status
agent-sessions checkpoint
```

Checkpointing refuses to stop anything until every active Codex or Claude pane
has a validated UUID. If a remote client cannot be identified, register the ID
reported by the agent and retry:

```bash
agent-sessions register --pane %21 --agent codex --session-id <UUID>
```

The checkpoint saves tmux while every pane still exists, interrupts active
turns, rechecks which agents remain before sending `/exit`, and retries one slow
cancellation within a 30-second bound. It never force-kills an agent. When a
pane uses the managed Codex app-server, checkpoint stops its daemon after every
recorded pane exits; restore starts it before reattaching. Use `--keep-running`
to save without exiting anything.

After rebooting, start tmux and press `C-a C-r` to restore its structure. Review
the proposed native resume commands before launching them:

```bash
agent-sessions restore
agent-sessions restore --run
```

`C-a S` opens the checkpoint command in a popup. `C-a R` opens the confirmed
agent restore command after the tmux structure exists. Automatic agent relaunch
is deliberately disabled. Restore records the new pane identities so subsequent
checkpoints do not require another manual remote-session registration.

## Agent resource headroom

Interactive `codex`, `claude`, and `gemini` commands run through `agent-run`.
Their processes and local build/test children share `agents.slice`, which caps
them at twelve CPUs and gives them less CPU weight than interactive desktop
applications. This leaves nominal four-CPU headroom on the sixteen-CPU laptop.
The managed Codex app-server and restored tmux sessions use the same launcher.

Docker containers do not inherit the user slice and remain outside this initial
limit.

## Neovim Go workflow

Go formatting is handled by Conform (`goimports`, then `gofumpt`). Live Go
diagnostics come from `gopls`, including Staticcheck and vulnerability import
analysis. Go linting and full validation are explicit terminal commands rather
than save-time lint hooks:

- `:GoLint` runs `golangci-lint run ./...`, respecting project-local config and
  custom local `bin/golangci-lint` builds.
- `:GoVet` runs `go vet ./...`.
- `:GoVulnCheck` runs `govulncheck ./...`.
- `:GoVerify` runs `go test ./...`, `go vet ./...`, `govulncheck ./...`, and
  `golangci-lint run ./...`.

Those commands are the same command-line tools made available to agents by the
dev setup: `go`, `gopls`, `golangci-lint`, and `govulncheck` are installed on
PATH, with `~/go/bin` included for Go tools installed via `go install`.

## Home Assistant

`bin/ha` is the general Home Assistant CLI for reading entity state, searching
entities, calling services, and fetching dashboard config.

`bin/ha-dashboard` updates Lovelace dashboards through the Home Assistant websocket
API instead of editing `.storage` files and restarting Home Assistant.

It expects:

- `HOME_ASSISTANT_TOKEN` to contain a long-lived access token
- `HOME_ASSISTANT_URL` to point at your instance

Examples:

```bash
uv run bin/ha state sensor.battery_soc
uv run bin/ha attrs media_player.downstairs
uv run bin/ha search predbat
uv run bin/ha dashboard get-config --pretty
```

```bash
uv run bin/ha-dashboard get-config --pretty
```

```bash
uv run bin/ha-dashboard upsert-card \
  --view-title Home \
  --title "Home NAS" \
  --after-title "Predbat" \
  --card-file /tmp/home-nas-card.json
```

### Lawn timelapse

`bin/lawn-timelapse` manages the rear lawn growth timelapse snapshots and
rendering.

```bash
bin/lawn-timelapse snapshot
bin/lawn-timelapse status
bin/lawn-timelapse install-renderer
bin/lawn-timelapse mount-command
bin/lawn-timelapse render-local
bin/lawn-timelapse render-local-smooth
bin/lawn-timelapse render-nas
bin/lawn-timelapse render-nas-smooth
```

The Home Assistant automation stores 4K snapshots under
`/config/www/lawn-timelapse`, which maps to
`/mnt/home-nas/docker/homeassistant/www/lawn-timelapse` when the NAS
`/volume1` export is mounted locally at `/mnt/home-nas`. Local rendering uses
the workstation ffmpeg and produces MP4 when `libx264` is available. The
Synology ffmpeg build can render an MJPEG AVI fallback.

The smoothed render uses the same timestamp across days, defaulting to
`14:00:00`, and writes `lawn-timelapse-smooth-latest.mp4`.

### Monitor colour

`bin/monitor-colour` inspects GNOME/colord display profiles and can reapply
the standard sRGB profile to the desk monitors.

```bash
bin/monitor-colour list
bin/monitor-colour apply-srgb
```

Run `apply-srgb` after the Dell S2725QS and BenQ EL2870U are connected and
visible in GNOME Displays. The monitors themselves should also be set to sRGB
mode in their OSD menus.

## Setup profiles

`hooks/post-up` is profile-driven. By default, `PROFILE=link`, which does not install host packages.

### Controls

- `PROFILE=link|core|dev|full`
- `SHELL_DEFAULT=1|0` (default `1`; set `0` to skip login shell update)
- `NODE_VERSION=<version>` (default `lts/*`)
- `GO_MIN_VERSION=<version>` (optional; default `1.23.0`)
- `GO_VERSION=<version>` (optional; pin the exact Go release to install locally, e.g. `1.23.12`)
- `GOLANGCI_LINT_VERSION=<tag>` (optional; default `v2.8.0`)
- `GOVULNCHECK_VERSION=<version>` (optional; default `latest`)
- `GPLS_VERSION=<version>` (optional; default `latest`)

### What gets configured

- On every profile (including `link`), installs Ghostty's `xterm-ghostty` terminfo into `~/.terminfo` from [config/ghostty/xterm-ghostty.terminfo](config/ghostty/xterm-ghostty.terminfo), so SSHing into the host from a Ghostty terminal does not break `tmux`/`vim` with "missing or unsuitable terminal: xterm-ghostty". Run standalone with `make ghostty-terminfo`.
- `PROFILE=core|dev|full` installs Ghostty from apt when available, falling back to Snap only when apt has no candidate. Run standalone with `make ghostty`.
- `PROFILE=core|dev|full` installs the Bruno desktop app from its official apt repository and the `bru` CLI through mise. Run standalone with `make bruno`.
- Python tooling via `uv`.
- Node tooling via `nvm`.
- `PROFILE=core|dev|full` bootstraps zplug plugins and installs missing TPM plugins. Run standalone with `make tmux-plugins`.
- `PROFILE=dev|full` installs additive Codex and Claude session checkpoint hooks. Run standalone with `make agent-session-hooks`.
- `PROFILE=dev|full` runs a headless lazy.nvim sync for the mise-managed Neovim (pinned in [config/mise/config.toml](config/mise/config.toml)).

### Profiles

- `link`: no host package/tool installs; dotfiles only.
- `core`: infra/network baseline (`tailscale`, `cloudflared`, `openconnect`, `wireguard-tools`, `nmap`, `tcpdump`, `dnsutils`, `jq`, `yq`, `traceroute`, `ufw`, `rsync`, `restic`, `rclone`) and Docker Compose v2 (`docker compose`).
- `core` also installs `mise` and all mise-managed CLIs from [config/mise/config.toml](config/mise/config.toml), bootstraps `FiraCode Nerd Font` into `~/.local/share/fonts/NerdFonts/FiraCode` (override with `NERD_FONT_NAME` / `NERD_FONT_VERSION`), and configures GNOME Terminal default font to `FiraCode Nerd Font Mono 11` (override with `TERMINAL_FONT_SPEC`).
- `core` installs the repo-managed AppArmor profile at [config/apparmor/bwrap](config/apparmor/bwrap) so Ubuntu 24.04's unprivileged user namespace restriction permits Bubblewrap-based sandboxes used by Codex CLI.
- Vale uses the repo-managed global config at [config/vale/vale.ini](config/vale/vale.ini), with the `general` profile: `Vale + write-good + alex`.
- `core` writes Zsh completions for `kubectl` to `${XDG_DATA_HOME:-$HOME/.local/share}/zsh/site-functions/_kubectl`.
- `PROFILE=dev|full` installs Go developer tools (`gopls`, `golangci-lint`, `govulncheck`, `modvendor`) via `go install`, installs TLA+ validation/proof tooling (`tlc`, `sany`, `pcal`, `tla2tex`, `apalache-mc`, `tlapm`, `tla`, `tla-mcp`), and writes Zsh completions for `kubebuilder`, Helm, and `kind`. (All mise-managed CLIs, including the dev tooling, come from `config.toml` at the `core` step above.)
- `dev`: `core` + developer tools such as `1password-cli`, `ansible`, `go`, `tofu` (OpenTofu), `doctl`, `gh`, `aws`, `openstack`, `hugo`, `picocom`, Claude Code (`@anthropic-ai/claude-code`), Codex CLI (`@openai/codex`), Gemini CLI (`@google/gemini-cli`), and ESP tooling (`esptool` + `idf.py` bootstrap), plus Neovim bootstrap.
- Go is installed from the official tarball into `~/.local/opt/go` with `~/.local/bin/go` symlinked ahead of system Go, so the repo can enforce a minimum version.
- `full`: `dev` + heavier extras such as `nerdctl`, `regctl`, `vegeta`, `oci-cli`, `autopep8`, and YubiKey tooling from [hooks/os](hooks/os).

Use OpenTofu (`tofu`) instead of Terraform.

### Bruno

Bruno stores API collections as files, so agents can inspect, edit, and run
them without desktop automation. From a collection directory:

```bash
bru run
bru run --env local --reporter-json /tmp/bruno-results.json
```

New shells expose `bru` directly. An agent process that predates installation
can bypass its stale `PATH` with `mise exec -- bru run`.

The CLI defaults to its safe script sandbox. Pass `--sandbox=developer` only
when a trusted collection needs filesystem access or external npm packages.

### Examples

```bash
# dotfiles + selected setup profile
make setup PROFILE=link
make setup PROFILE=core
make setup PROFILE=dev
make setup PROFILE=full

# bootstrap host dependencies, then run selected setup profile
make bootstrap PROFILE=dev
make bootstrap PROFILE=full

# override Node channel and shell default behavior
NODE_VERSION=lts/* SHELL_DEFAULT=0 make setup PROFILE=dev
```

## GNOME extension preferences

Clipboard Indicator and Caffeine preferences can be versioned in this repo:

```bash
make gnome-prefs-save
make gnome-prefs-apply
```

This stores/loads:

- `config/gnome/clipboard-indicator.dconf`
- `config/gnome/caffeine.dconf`

## Kubernetes installers (no `curl | bash`)

Fast-moving CLI tools are managed centrally in [config/mise/config.toml](config/mise/config.toml)
— the single source of truth. Add or pin a tool there and it installs on the next
`make setup` (or `mise install`); there is no parallel list in `hooks/os` to keep in
sync. Update a version, then run:

```bash
mise install
```

Personal, machine-local tools (e.g. tools you only want on a personal laptop) go in
an untracked `~/.config/mise/config.local.toml`, which mise loads automatically.

`kind` is the default local Kubernetes cluster tool for controller-manager
development. It is installed by the `dev` and `full` profiles through mise.

`tuicr` is installed by the `dev` and `full` profiles through mise for local
PR-style review of worktree changes before folding them into the main checkout.

Manual Kubernetes installers remain available for `k3d` only:

```bash
source hooks/kubernetes
kube::install_k3d
```

`kubectl` and `vale` are installed automatically by `make setup PROFILE=core|dev|full`.
Helm, `kubebuilder`, `kind`, `gh`, `tuicr`, `kubectx`, `kubens`, `promtool`, `awscli`, `python-openstackclient` with the Octavia plugin, `esptool`, `black`, `isort`, `mypy`, and `ruff` are installed automatically by `make setup PROFILE=dev|full`.
`oci-cli` and `autopep8` are installed automatically by the `full` profile extras from the same mise config.
The repo-managed [config/mise/config.toml](config/mise/config.toml) is linked to `~/.config/mise/config.toml`, and the hooks pass `MISE_GLOBAL_CONFIG_FILE` so tools install even before the config is linked.
Vale's global config lives at `~/.config/vale/vale.ini` and setup runs `vale sync` to install the configured style packages.

## TLA+ tooling

`PROFILE=dev|full` installs command-line tooling for validating and proving TLA+ models:

- `tlc`, `sany`, `pcal`, `tla2tex`, `tlatex`, `tlarepl`, and `tla2tools` wrappers around `tla2tools.jar`
- `apalache-mc` for symbolic model checking
- `tlapm` from TLAPS for proof checking
- `tla` and `tla-mcp` from the experimental `tla-rs` project for interactive/model-checking workflows and MCP-enabled agent clients

Install or verify just this toolchain with:

```bash
make tla-tools
make verify-tla-tools
```

The installers place artifacts under `~/.local/opt` and symlink commands into `~/.local/bin`.

### LLM-assisted TLA+ workflow

Use the LLM as a drafting and repair assistant, not as the verifier:

1. Write a modeling brief first: system boundary, state variables, actions, invariants, expected liveness, and explicit non-goals.
2. Ask the LLM to produce a small TLA+ module and `.cfg`, then immediately run `sany`, `tlc`, and, when useful, `apalache-mc`.
3. Keep model constants tiny until the spec converges. Increase bounds only after SANY/TLC failures stop being modeling mistakes.
4. Treat counterexamples as design evidence. Classify each as an invalid invariant, a spec/modeling gap, or a real implementation bug.
5. For implementation conformance, add trace validation: instrument code to emit NDJSON events, replay those traces against a TLA+ trace spec, then model check.
6. For proof obligations, use `tlapm` after the finite model stabilizes. Do not ask the LLM to assert a proof succeeded; run TLAPS.

`tla-mcp` is registered as the global Codex MCP server `tla` on this machine. It gives agent clients quick model-checking tools through the experimental `tla-rs` checker. Use official TLC/TLAPS results as the source of truth when behavior differs.

Installed local Codex skills from Specula support the agent workflow after restarting Codex:

- `$spec-generation`
- `$harness-generation`
- `$tla-checking-workflow`
- `$tla-trace-workflow`
- `$tla-verification-workflow`

## Desk light helper (Home Assistant + tray icon)

`$HOME/bin/desk-light-helper` can auto-toggle your desk LED strip when all are true:

- your laptop appears docked (via configurable `lsusb` regex)
- Home Assistant is reachable

Repo-managed config lives at `config/desk-light-helper/config.toml` and defaults to:

- HA URL: `https://hass.prydie.co.uk/`
- light entity: `light.office_player_sk6812_light`
- HA token from env var `HOME_ASSISTANT_TOKEN`

Setup:

```bash
make up
export HOME_ASSISTANT_TOKEN='your-long-lived-access-token'
$HOME/bin/desk-light-helper
```

Use `$HOME/bin/desk-light-helper` for manual runs if `~/bin` is not on `PATH`.
Use tray menu options to switch between automatic mode and manual force on/off.
Logs are emitted to stderr/stdout so they are visible in terminal runs and in
`journalctl` when run via systemd.

Recommended startup via user service:

1. Ensure `HOME_ASSISTANT_TOKEN` is exported in `~/.zshrc.local`
   (or set it in `~/.config/desk-light-helper/env`).
2. Enable and start:
   `systemctl --user daemon-reload`
   `systemctl --user enable --now desk-light-helper.service`
3. Follow logs:
   `journalctl --user -u desk-light-helper.service -f`

## LAN device discovery (router API)

`$HOME/bin/lan-discover` reads device inventory directly from a Sagemcom router API instead of probing the LAN.

The current implementation is router-first and uses:

- `POST /api/v1/login`
- `GET /api/v1/hosts`
- `GET /api/v1/dhcp/clients`
- optional `GET /api/v1/hosts/arp_table`

Keep credentials out of this repo. Store them in a local config file or environment variables instead:

```toml
# ~/.config/lan-discover/config.toml
[router]
url = "https://192.168.1.1"
username = "admin"
password_env = "LAN_DISCOVER_ROUTER_PASSWORD"
```

Then export the password outside the repo, for example in `~/.zshrc.local`:

```bash
export LAN_DISCOVER_ROUTER_PASSWORD='your-router-password'
```

Usage:

```bash
$HOME/bin/lan-discover
$HOME/bin/lan-discover --active-only
$HOME/bin/lan-discover --include-arp
$HOME/bin/lan-discover --json
```

Notes:

- TLS verification is off by default because local router certs are commonly self-signed.
- The script keeps the router session cookie in memory only.
- `hosts` is treated as the primary inventory; `dhcp/clients` is merged in for reservation and naming data.
- DHCP reservations are preserved separately from current live IPs.

## Router Prometheus exporter

`$HOME/bin/router-metrics-exporter` exposes a small Prometheus endpoint for the Sagemcom/YouFibre router.

It currently exports:

- WAN up/down state
- WAN RX/TX packets, bytes, errors, discards
- Per-interface counters and link state from `lan/stats`
- Session count
- Network info labels (public IPv4/IPv6, gateways, MAC)
- Host inventory counts
- Host inventory grouped by link/type/device type
- DHCP reservation counts

It uses the same local-only credentials pattern as `lan-discover`; do not commit secrets.

Authentication notes:

- The exporter mirrors the router web UI login flow rather than posting the raw password directly.
- It first calls `/api/v1/login-params`, then derives the challenge response expected by `/api/v1/login`.
- Login attempts back off exponentially on HTTP `429` so a rate-limited router is not hammered every scrape.

One-shot test:

```bash
ROUTER_EXPORTER_USERNAME=admin \
ROUTER_EXPORTER_PASSWORD='your-router-password' \
$HOME/bin/router-metrics-exporter --once
```

Server mode:

```bash
ROUTER_EXPORTER_USERNAME=admin \
ROUTER_EXPORTER_PASSWORD='your-router-password' \
$HOME/bin/router-metrics-exporter
```

The default listener is `0.0.0.0:9787` and the default path is `/metrics`.

The default metric set is intentionally low-cardinality for long-term Prometheus use; it exports host counts and grouped summaries rather than one time series per device.

The script is also structured to be imported if needed:

- Shared API logic lives in the local `tools/router/router_api/` package and is used by both `lan-discover` and the exporter.
- The import surface is re-exported from `tools/router/router_api/__init__.py`, with the implementation in `tools/router/router_api/client.py`.
- `RouterClient` can be reused by other local tools that need authenticated API access
- `render_metrics()` can be called directly if you want to expose the same metric set from another entrypoint
- The module has no side effects on import; network access only starts when the client is used

Logging:

- The exporter now uses Python's standard logging module instead of ad-hoc `print()` calls.
- Set `ROUTER_EXPORTER_LOG_LEVEL` (or pass `--log-level`) to control verbosity. The default is `INFO`.

A minimal container build is included at `tools/router/container/` with:

- `tools/router/container/Dockerfile`
- `tools/router/container/docker-compose.example.yml`

Prometheus scrape example:

```yaml
- job_name: 'router'
  metrics_path: /metrics
  static_configs:
    - targets: ['router-metrics-exporter:9787']
```

## Backups to Synology NAS (Restic)

This repo now includes a repo-managed `restic` wrapper + user `systemd` timers so both desktop and laptop can use the same backup workflow while keeping NAS credentials local.

### What is versioned vs local

- Versioned in dotfiles:
  - backup command wrapper: `bin/restic-backup`
  - verification wrapper: `bin/restic-verify`
  - workstation bootstrap helper: `bin/restic-workstation-setup`
  - timer/service units: `config/systemd/user/restic-*.{service,timer}`
- default include/exclude lists: `config/restic-backup/paths.txt`, `config/restic-backup/excludes.txt`
- Local per machine (not in git):
  - `~/.config/restic-backup/env`
  - `~/.config/restic-backup/password`
  - optional host/local overrides (`paths.local.txt`, `paths.<hostname>.txt`, etc.)

### Setup (each machine)

1. Link dotfiles and ensure `restic` is installed (included in `PROFILE=core|dev|full`).
2. Bootstrap local workstation config (recommended):

```bash
./bin/restic-workstation-setup --write-ssh-config
```

This generates a dedicated SSH key (`~/.ssh/id_ed25519_home_nas_backup`), creates local `restic` config/password files, and adds a local `home-nas-backup` SSH alias block.

If you prefer to avoid modifying `~/.ssh/config`, omit `--write-ssh-config` and use the printed SSH snippet/manual setup.

3. (Manual alternative) Create local config files:

```bash
mkdir -p ~/.config/restic-backup
cp ~/.config/restic-backup/env.example ~/.config/restic-backup/env
chmod 600 ~/.config/restic-backup/env
printf 'choose-a-strong-restic-password\n' > ~/.config/restic-backup/password
chmod 600 ~/.config/restic-backup/password
```

4. Edit `~/.config/restic-backup/env` and set `RESTIC_REPOSITORY`.
   Examples:
   - `sftp:backup@nas.lan:/volume1/restic/workstations` (Synology SSH/SFTP)
   - `sftp:backup@home-nas-backup:/volume1/Backups/restic/workstations` (recommended with local SSH alias)
   - `/mnt/nas-backups/restic/workstations` (mounted SMB/NFS share)
5. Review backup scope in `config/restic-backup/paths.txt` and `config/restic-backup/excludes.txt`.
   Default is now `~` (whole home) with broad cache/build/VCS excludes.
6. Initialize the repo once (from one machine):

```bash
~/bin/restic-backup init
```

7. Test and enable timers:

```bash
make restic-backup-dry-run
make restic-backup-now
make restic-verify-now
make restic-systemd-enable
```

### Operations

```bash
make restic-snapshots
make restic-maintenance-now
make restic-verify-now
journalctl --user -u restic-verify.service -f
journalctl --user -u restic-backup.service -f
```

### Notes

- The wrapper auto-loads shared + host-specific include/exclude files:
  - `paths.txt`, `paths.<hostname>.txt`, `paths.local.txt`
  - `excludes.txt`, `excludes.<hostname>.txt`, `excludes.local.txt`
- Missing paths are skipped with a warning (useful when desktop/laptop differ).
- Defaults back up `~` and exclude `.git` plus common cache/build directories to keep backups focused on durable data/state.
- Use `excludes.<hostname>.txt` or `excludes.local.txt` for machine-specific heavy paths you do not care about (for example VM images, game libraries, media scratch dirs).
- Verification is intentionally laptop-friendly by default: snapshot freshness warns at 7 days and goes critical at 30 days (`bin/restic-verify`).

### Optional Verification + Home Assistant Webhook

Add these to `~/.config/restic-backup/env` if you want freshness status pushed to Home Assistant (or any webhook-compatible receiver):

```bash
RESTIC_VERIFY_WARN_AGE_HOURS=168   # 7 days
RESTIC_VERIFY_CRIT_AGE_HOURS=720   # 30 days
RESTIC_HA_WEBHOOK_URL="https://homeassistant.example.com/api/webhook/your-webhook-id"
```

The weekly `restic-verify.timer` posts JSON status after each freshness check when `RESTIC_HA_WEBHOOK_URL` is set.

## Safety notes

- Destructive cleanup is guarded and requires `ALLOW_DESTRUCTIVE=1`.
- Host package/tool installation is opt-in, never implicit.
- `hooks/os` no longer auto-runs installers when sourced.

## Inspiration

- https://github.com/nicksp/dotfiles
- https://github.com/thoughtbot/dotfiles
