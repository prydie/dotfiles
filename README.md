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
make refresh-dev
make gnome-prefs-save
make gnome-prefs-apply
make restic-backup-now
make restic-systemd-enable
make patching
make patching-full
```

## Setup profiles

`hooks/post-up` is profile-driven. By default, `PROFILE=link`, which does not install host packages.

### Controls

- `PROFILE=link|core|dev|full`
- `SHELL_DEFAULT=1|0` (default `1`; set `0` to skip login shell update)
- `NODE_VERSION=<version>` (default `lts/*`)
- `ATUIN_VERSION=<tag>` (optional; pin Atuin install version, e.g. `v18.8.0`)

### What gets configured

- Python tooling via `uv`.
- Node tooling via `nvm`.
- `PROFILE=core|dev|full` bootstraps zplug plugins and TPM.
- `PROFILE=dev|full` ensures Neovim >= `0.11.0` (local install fallback) and runs headless lazy.nvim sync.

### Profiles

- `link`: no host package/tool installs; dotfiles only.
- `core`: infra/network baseline (`tailscale`, `cloudflared`, `openconnect`, `wireguard-tools`, `nmap`, `tcpdump`, `dnsutils`, `jq`, `yq`, `traceroute`, `ufw`, `rsync`, `restic`, `rclone`) and Docker Compose v2 (`docker compose`).
- `core` also installs Atuin, bootstraps `FiraCode Nerd Font` into `~/.local/share/fonts/NerdFonts/FiraCode` (override with `NERD_FONT_NAME` / `NERD_FONT_VERSION`), and configures GNOME Terminal default font to `FiraCode Nerd Font Mono 11` (override with `TERMINAL_FONT_SPEC`).
- `dev`: `core` + developer tools such as `ansible`, `go`, `tofu` (OpenTofu), `doctl`, `aws`, `hugo`, `picocom`, Codex CLI (`@openai/codex`), Gemini CLI (`@google/gemini-cli`), and ESP tooling (`esptool` + `idf.py` bootstrap), plus Neovim bootstrap.
- `full`: `dev` + heavier extras from `hooks/os` (`tools::full_install`).

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

For explicit, pinned installers with checksum verification:

```bash
source hooks/kubernetes
kube::install_kubectl
kube::install_helm
kube::install_k3d
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

It also installs an autostart entry at `config/autostart/desk-light-helper.desktop`.
Use `$HOME/bin/desk-light-helper` for manual runs if `~/bin` is not on `PATH`.
Use tray menu options to switch between automatic mode and manual force on/off.
Logs are emitted to stderr/stdout so they are visible in terminal runs and in
`journalctl` when run via systemd.

Optional (recommended) user service:

1. Ensure `HOME_ASSISTANT_TOKEN` is exported in `~/.zshrc.local`
   (or set it in `~/.config/desk-light-helper/env`).
2. Disable desktop autostart entry if you only want systemd-managed startup.
3. Enable and start:
   `systemctl --user daemon-reload`
   `systemctl --user enable --now desk-light-helper.service`
4. Follow logs:
   `journalctl --user -u desk-light-helper.service -f`

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
