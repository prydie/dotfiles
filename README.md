# Andrew Pryde's dotfiles

Personal dotfiles managed with [`rcm`](https://github.com/thoughtbot/rcm).

## Scope

This repo contains shell/editor/tmux/git config and optional host bootstrap hooks.

- Safe default: `make up` only links dotfiles.
- Opt-in setup: `hooks/post-up` can install packages/plugins/tools via flags.

## Requirements

- Linux (Debian/Ubuntu recommended for bootstrap scripts)
- `git`, `make`, `rcm` (`install.sh` bootstraps these on Debian/Ubuntu)
- `uv` (installed automatically during package setup)

## Quick start

One-line bootstrap (fresh Ubuntu):

```bash
sudo apt-get update && sudo apt-get install -y git make && git clone https://github.com/prydie/dotfiles.git ~/.dotfiles && cd ~/.dotfiles && make bootstrap-all
```

If you prefer SSH auth (recommended when you will push changes):

```bash
sudo apt-get update && sudo apt-get install -y git make && git clone git@github.com:prydie/dotfiles.git ~/.dotfiles && cd ~/.dotfiles && make bootstrap-all
```

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
make bootstrap-all
make bootstrap-full
make post-up
```

## Post-up flags

`hooks/post-up` supports optional setup stages:

- `INSTALL_PACKAGES=1` installs apt/snap packages
- `PACKAGE_PROFILE=core|dev` chooses package tier (`core` default, `dev` installs core+dev)
- `INSTALL_NVIM=1` runs Neovim bootstrap
- `FULL_SETUP=1` runs extra heavy tool installers from `hooks/os`
- `SET_ZSH_DEFAULT=0` skips setting your login shell to `zsh` (default behavior is to set it)

Python tooling is managed with `uv` (virtualenv + tool installs).
Node tooling is managed with `nvm` (`NVM_NODE_VERSION` defaults to `lts/*`).
`dev` profile includes `ansible`, `go`, `tofu` (OpenTofu), `doctl`, `aws`, `hugo`, `picocom`, Codex CLI (`@openai/codex`), Gemini CLI (`@google/gemini-cli`), and ESP tooling (`esptool` + `idf.py` bootstrap).
Docker Compose v2 (`docker compose`) is ensured; use OpenTofu (`tofu`) instead of Terraform.
Infra/network baseline is part of default `core` install (`tailscale`, `cloudflared`, `openconnect`, `wireguard-tools`, `nmap`, `tcpdump`, `dnsutils`, `jq`, `yq`, `traceroute`, `ufw`, `rsync`, `restic`, `rclone`).
Default `core` install also bootstraps `FiraCode Nerd Font` into `~/.local/share/fonts/NerdFonts/FiraCode` (override with `NERD_FONT_NAME` / `NERD_FONT_VERSION`) and configures the GNOME Terminal default profile font to `FiraCode Nerd Font Mono 11` (override with `TERMINAL_FONT_SPEC`).
`post-up` also bootstraps zplug plugin installs and TPM; `INSTALL_NVIM=1` ensures Neovim >= `0.11.0` (local install fallback) and runs headless lazy.nvim sync.

Examples:

```bash
INSTALL_PACKAGES=1 make post-up
INSTALL_PACKAGES=1 PACKAGE_PROFILE=core make post-up
INSTALL_PACKAGES=1 PACKAGE_PROFILE=dev make post-up
NVM_NODE_VERSION=lts/* INSTALL_PACKAGES=1 PACKAGE_PROFILE=dev make post-up
INSTALL_PACKAGES=1 INSTALL_NVIM=1 make post-up
INSTALL_PACKAGES=1 INSTALL_NVIM=1 FULL_SETUP=1 make post-up
```

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
