#!/usr/bin/env make

SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

DOTFILES_DIR ?= $(HOME)/.dotfiles
RCRC ?= $(DOTFILES_DIR)/rcrc
OPERATOR_NAME ?= Andrew Pryde
ALLOW_DESTRUCTIVE ?= 0
PROFILE ?= link
SHELL_DEFAULT ?= 1
NODE_VERSION ?= lts/*

.PHONY: help
help: ## Show available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) | \
		sort | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  %-20s %s\n", $$1, $$2}'

.PHONY: up
up: ## Symlink dotfiles with rcm (rcup)
	@echo "Bringing up $(OPERATOR_NAME)'s dotfiles"
	@command -v rcup >/dev/null || { echo "rcup not found. Install rcm first."; exit 1; }
	@env RCRC="$(RCRC)" rcup

.PHONY: setup
setup: ## Run host setup profile (PROFILE=link|core|dev|full)
	@PROFILE="$(PROFILE)" SHELL_DEFAULT="$(SHELL_DEFAULT)" NODE_VERSION="$(NODE_VERSION)" bash hooks/post-up

.PHONY: codex-sandbox-fix
codex-sandbox-fix: ## Install AppArmor profile needed by Codex CLI bubblewrap sandbox
	@bash -lc 'source hooks/os; os::ubuntu::ensure_bwrap_apparmor_profile'

.PHONY: codex-superpowers
codex-superpowers: ## Install/enable the Codex Superpowers plugin
	@bash hooks/os codex-superpowers

.PHONY: tmux-plugins
tmux-plugins: ## Install tmux TPM plugins
	@bash hooks/os tmux-plugins

.PHONY: ai-skills
ai-skills: ## Install the mattpocock/skills pilot subset for Claude Code and Codex
	@bash hooks/os ai-skills

.PHONY: tla-tools
tla-tools: ## Install and verify TLA+ validation/proof tooling
	@bash hooks/os tla-tools

.PHONY: verify-tla-tools
verify-tla-tools: ## Verify TLA+ validation/proof tooling is callable
	@bash hooks/os verify-tla-tools

.PHONY: ghostty-terminfo
ghostty-terminfo: ## Install Ghostty's xterm-ghostty terminfo into ~/.terminfo (for SSH from Ghostty)
	@bash hooks/os ghostty-terminfo

.PHONY: ghostty
ghostty: ## Install Ghostty, using apt before snap fallback
	@bash hooks/os ghostty

.PHONY: bruno
bruno: ## Install Bruno API client desktop app and CLI
	@bash hooks/os bruno

.PHONY: bootstrap
bootstrap: ## Install bootstrap deps, link dotfiles, and run setup profile (PROFILE=link|core|dev|full)
	@bash install.sh
	@$(MAKE) setup PROFILE="$(PROFILE)" SHELL_DEFAULT="$(SHELL_DEFAULT)" NODE_VERSION="$(NODE_VERSION)"

.PHONY: clean-house
clean-house: ## Destructive cleanup. Requires ALLOW_DESTRUCTIVE=1
	@if [ "$(ALLOW_DESTRUCTIVE)" != "1" ]; then \
		echo "Refusing destructive cleanup. Re-run with ALLOW_DESTRUCTIVE=1"; \
		exit 1; \
	fi
	@rm -rf "$(HOME)/.local/bin"

.PHONY: sys-info
sys-info: ## Print basic system info
	@echo ""
	@echo "System Info"
	@echo "-----------"
	@echo "Owner: $(OPERATOR_NAME)"
	@echo ""
	@echo "Host Name: $$(hostname)"
	@echo ""
	@echo "Kernel: $$(uname -r)"
	@echo ""
	@echo "Routes:"
	@ip route show || true
	@echo ""
	@echo "Loopback interface:"
	@ip address show lo || true
	@echo ""
	@echo "Boot partition usage:"
	@df /boot/ -h || true
	@echo ""

.PHONY: patching
patching: sys-info ## Run apt patch cycle and reboot
	@echo "Patching host..."
	@sudo apt update -y
	@sudo apt upgrade -y
	@sudo apt autoremove -y
	@$(MAKE) firmware-overrides
	@sudo update-grub
	@sudo shutdown -r now

.PHONY: firmware-overrides
firmware-overrides: ## Install managed local firmware overrides
	@tools/xe_lnl_guc_firmware_override.sh install

.PHONY: refresh-dev
refresh-dev: ## Refresh user-level tooling/plugins (zplug, tmux TPM, Neovim lazy)
	@if [ -s "$(HOME)/.zplug/init.zsh" ] && command -v zsh >/dev/null 2>&1; then \
		echo "Updating zplug plugins..."; \
		zsh -lc 'source "$(HOME)/.zplug/init.zsh"; zplug update || true'; \
	else \
		echo "Skipping zplug update (zplug/zsh not available)"; \
	fi
	@if [ -x "$(HOME)/.tmux/plugins/tpm/bin/update_plugins" ]; then \
		echo "Updating tmux TPM plugins..."; \
		"$(HOME)/.tmux/plugins/tpm/bin/update_plugins" all || true; \
	elif [ -x "$(HOME)/.tmux/plugins/tpm/bin/install_plugins" ]; then \
		echo "Installing tmux TPM plugins..."; \
		"$(HOME)/.tmux/plugins/tpm/bin/install_plugins" || true; \
	else \
		echo "Skipping tmux TPM update (TPM not installed)"; \
	fi
	@if [ -x "$(HOME)/.local/bin/nvim" ]; then \
		echo "Syncing Neovim plugins with lazy.nvim using $(HOME)/.local/bin/nvim..."; \
		"$(HOME)/.local/bin/nvim" --headless "+Lazy! sync" +qa || true; \
	elif command -v nvim >/dev/null 2>&1; then \
		echo "Syncing Neovim plugins with lazy.nvim..."; \
		nvim --headless "+Lazy! sync" +qa || true; \
	else \
		echo "Skipping Neovim plugin sync (nvim not installed)"; \
	fi

.PHONY: gnome-prefs-save
gnome-prefs-save: ## Save GNOME clipboard/caffeine extension prefs to config/gnome/*.dconf
	@mkdir -p config/gnome
	@command -v dconf >/dev/null 2>&1 || { echo "dconf not found"; exit 1; }
	@dconf dump /org/gnome/shell/extensions/clipboard-indicator/ > config/gnome/clipboard-indicator.dconf
	@dconf dump /org/gnome/shell/extensions/caffeine/ > config/gnome/caffeine.dconf
	@echo "Saved GNOME extension preferences to config/gnome/"

.PHONY: gnome-prefs-apply
gnome-prefs-apply: ## Apply GNOME clipboard/caffeine extension prefs from config/gnome/*.dconf
	@command -v dconf >/dev/null 2>&1 || { echo "dconf not found"; exit 1; }
	@if [ -s config/gnome/clipboard-indicator.dconf ]; then \
		dconf load /org/gnome/shell/extensions/clipboard-indicator/ < config/gnome/clipboard-indicator.dconf; \
	fi
	@if [ -s config/gnome/caffeine.dconf ]; then \
		dconf load /org/gnome/shell/extensions/caffeine/ < config/gnome/caffeine.dconf; \
	fi
	@echo "Applied GNOME extension preferences"

.PHONY: patching-full
patching-full: refresh-dev sys-info ## Refresh user plugins, patch apt packages, and reboot
	@echo "Refreshing dev tools completed; now patching host..."
	@sudo apt update -y
	@sudo apt upgrade -y
	@sudo apt autoremove -y
	@$(MAKE) firmware-overrides
	@sudo update-grub
	@sudo shutdown -r now

.PHONY: restic-backup-now
restic-backup-now: ## Run restic backup now (requires ~/.config/restic-backup/env)
	@"$(HOME)/bin/restic-backup" backup

.PHONY: restic-backup-dry-run
restic-backup-dry-run: ## Preview restic backup file selection
	@"$(HOME)/bin/restic-backup" dry-run

.PHONY: restic-snapshots
restic-snapshots: ## List restic snapshots
	@"$(HOME)/bin/restic-backup" snapshots

.PHONY: restic-maintenance-now
restic-maintenance-now: ## Run restic retention+prune now
	@"$(HOME)/bin/restic-backup" forget

.PHONY: restic-verify-now
restic-verify-now: ## Check restic snapshot freshness for this host
	@"$(HOME)/bin/restic-verify" freshness

.PHONY: restic-check-now
restic-check-now: ## Run restic repository check now
	@"$(HOME)/bin/restic-verify" check-lite

.PHONY: restic-systemd-enable
restic-systemd-enable: ## Enable/start user restic backup + maintenance + verify timers
	@systemctl --user daemon-reload
	@systemctl --user enable --now restic-backup.timer restic-maintenance.timer restic-verify.timer
	@systemctl --user list-timers --all | grep -E 'restic-(backup|maintenance|verify)\.timer' || true

.PHONY: restic-systemd-status
restic-systemd-status: ## Show recent restic timer/service status
	@systemctl --user status restic-backup.timer restic-maintenance.timer restic-verify.timer --no-pager || true
	@echo ""
	@systemctl --user status restic-backup.service restic-maintenance.service restic-verify.service --no-pager || true
