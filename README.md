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
make tla-tools
make verify-tla-tools
make ghostty-terminfo
make refresh-dev
make gnome-prefs-save
make gnome-prefs-apply
make restic-backup-now
make restic-systemd-enable
make patching
make patching-full
nks-dev doctor
nks-dev kind-create
nks-dev tunnel
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

`make setup PROFILE=dev|full` installs Codex CLI and enables the curated
`superpowers@openai-curated` plugin in local `~/.codex` state. To refresh or
install only that plugin, run:

```bash
make codex-superpowers
```

Generated Codex plugin cache/config remains local to `~/.codex` and is not
tracked by this public repo. Superpowers scratch state under `.superpowers/` is
also ignored; deliberate specs/plans under `docs/superpowers/` remain visible to
Git review.

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
- Python tooling via `uv`.
- Node tooling via `nvm`.
- `PROFILE=core|dev|full` bootstraps zplug plugins and TPM.
- `PROFILE=dev|full` installs pinned Neovim from [config/mise/config.toml](config/mise/config.toml) and runs headless lazy.nvim sync.

### Profiles

- `link`: no host package/tool installs; dotfiles only.
- `core`: infra/network baseline (`tailscale`, `cloudflared`, `openconnect`, `wireguard-tools`, `nmap`, `tcpdump`, `dnsutils`, `jq`, `yq`, `traceroute`, `ufw`, `rsync`, `restic`, `rclone`) and Docker Compose v2 (`docker compose`).
- `core` also installs `mise`, then installs Atuin, Starship, `kubectl`, and `vale` from [config/mise/config.toml](config/mise/config.toml), bootstraps `FiraCode Nerd Font` into `~/.local/share/fonts/NerdFonts/FiraCode` (override with `NERD_FONT_NAME` / `NERD_FONT_VERSION`), and configures GNOME Terminal default font to `FiraCode Nerd Font Mono 11` (override with `TERMINAL_FONT_SPEC`).
- `core` installs the repo-managed AppArmor profile at [config/apparmor/bwrap](config/apparmor/bwrap) so Ubuntu 24.04's unprivileged user namespace restriction permits Bubblewrap-based sandboxes used by Codex CLI.
- Vale uses the repo-managed global config at [config/vale/vale.ini](config/vale/vale.ini), with the `general` profile: `Vale + write-good + alex`.
- `core` writes Zsh completions for `kubectl` to `${XDG_DATA_HOME:-$HOME/.local/share}/zsh/site-functions/_kubectl`.
- `PROFILE=dev|full` also installs Neovim, Helm, `kubebuilder`, `kind`, `doctl`, `gh`, `tuicr`, `kubectx`, `kubens`, `promtool`, `awscli`, `python-openstackclient` with `python-octaviaclient`, `esptool`, `black`, `isort`, `mypy`, and `ruff` from [config/mise/config.toml](config/mise/config.toml), installs Go developer tools (`gopls`, `golangci-lint`, `govulncheck`, `modvendor`) via `go install`, installs TLA+ validation/proof tooling (`tlc`, `sany`, `pcal`, `tla2tex`, `apalache-mc`, `tlapm`, `tla`, `tla-mcp`), and writes Zsh completions for `kubectl`, `kubebuilder`, Helm, and `kind`.
- `dev`: `core` + developer tools such as `ansible`, `go`, `tofu` (OpenTofu), `doctl`, `gh`, `aws`, `openstack`, `hugo`, `picocom`, Codex CLI (`@openai/codex`), Gemini CLI (`@google/gemini-cli`), and ESP tooling (`esptool` + `idf.py` bootstrap), plus Neovim bootstrap.
- Go is installed from the official tarball into `~/.local/opt/go` with `~/.local/bin/go` symlinked ahead of system Go, so the repo can enforce a minimum version.
- `full`: `dev` + heavier extras such as `nerdctl`, `regctl`, `vegeta`, `oci-cli`, `autopep8`, and YubiKey tooling from [hooks/os](hooks/os).

Use OpenTofu (`tofu`) instead of Terraform.

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

Fast-moving CLI tools are managed centrally via [config/mise/config.toml](config/mise/config.toml). Update versions there, then run:

```bash
mise install
```

`kind` is the default local Kubernetes cluster tool for controller-manager
development. It is installed by the `dev` and `full` profiles through mise and
is managed by `nks-dev` for NKS-specific local clusters.

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
The repo-managed [config/mise/config.toml](config/mise/config.toml) is linked to `~/.config/mise/config.toml`, and the shell/hooks also export `MISE_GLOBAL_CONFIG_FILE` as a fallback when needed.
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

## NKS local development

`nks-dev` manages the generic local NKS development loop without committing
work-specific values to this public repo. It reads private settings from
`~/.config/nks-dev/env`; a placeholder template lives at
[config/nks-dev/env.example](config/nks-dev/env.example).

Bootstrap a private config:

```bash
mkdir -p ~/.config/nks-dev
nks-dev config-template > ~/.config/nks-dev/env
chmod 0600 ~/.config/nks-dev/env
$EDITOR ~/.config/nks-dev/env
```

Check the workstation and create a local management cluster:

```bash
nks-dev doctor
nks-dev kind-create
kubectl --context kind-nks-dev get nodes
```

The default cluster is one control-plane node plus two workers using a
digest-pinned `kindest/node` image and a local registry on `localhost:5001`.
Override those values in `~/.config/nks-dev/env`, not in this repo.

For dev OpenStack instances that need to reach a local service, configure the
reverse SSH tunnel variables in `~/.config/nks-dev/env`, then run:

```bash
nks-dev tunnel-command
nks-dev tunnel
```

On a replacement laptop, run the normal setup profile, restore
`~/.config/nks-dev/env` and any credentials from the private source of truth,
then recreate the cluster with `nks-dev kind-create`.

## UNI helpers

`uni-openstack` runs the OpenStack CLI against the UNI dev cloud, resolving the username and password from the `op://Employee/unikorn-dev-openstack` item at runtime. The OpenStack project and domain names default to the same `username` field; override the usual `OS_*` variables if they need to differ. Install `1password-cli` from the official apt package rather than mise so Linux desktop app integration can trust the `op` binary.

```bash
uni-openstack server list
uni-openstack loadbalancer list
```

`uni-clone-projects` clones `nscaledev` repositories tagged with `unikorn` using SSH URLs:

```bash
uni-clone-projects ~/src/nscaledev
```

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
