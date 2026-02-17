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

## Safety notes

- Destructive cleanup is guarded and requires `ALLOW_DESTRUCTIVE=1`.
- Host package/tool installation is opt-in, never implicit.
- `hooks/os` no longer auto-runs installers when sourced.

## Inspiration

- https://github.com/nicksp/dotfiles
- https://github.com/thoughtbot/dotfiles
