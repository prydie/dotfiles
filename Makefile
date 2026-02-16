#!/usr/bin/env make

SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

DOTFILES_DIR ?= $(HOME)/.dotfiles
RCRC ?= $(DOTFILES_DIR)/rcrc
OPERATOR_NAME ?= Andrew Pryde
ALLOW_DESTRUCTIVE ?= 0

.PHONY: help
help: ## Show available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) | \
		sort | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  %-20s %s\n", $$1, $$2}'

.PHONY: all
all: up ## Alias for up

.PHONY: up
up: ## Symlink dotfiles with rcm (rcup)
	@echo "Bringing up $(OPERATOR_NAME)'s dotfiles"
	@command -v rcup >/dev/null || { echo "rcup not found. Install rcm first."; exit 1; }
	@env RCRC="$(RCRC)" rcup

.PHONY: post-up
post-up: ## Run post-up host setup tasks
	@bash hooks/post-up

.PHONY: bootstrap
bootstrap: ## Install rcm and run up
	@bash install.sh

.PHONY: bootstrap-full
bootstrap-full: ## Install bootstrap deps, link dotfiles, install core packages, and bootstrap Neovim
	@bash install.sh
	@INSTALL_PACKAGES=1 PACKAGE_PROFILE=core INSTALL_NVIM=1 make post-up

.PHONY: bootstrap-all
bootstrap-all: ## Install bootstrap deps, link dotfiles, and run full dev setup (packages, Neovim, toolchain)
	@bash install.sh
	@INSTALL_PACKAGES=1 PACKAGE_PROFILE=dev INSTALL_NVIM=1 FULL_SETUP=1 make post-up

.PHONY: clean-local-bin
clean-local-bin: ## Remove ~/.local/bin
	@rm -rf "$(HOME)/.local/bin"

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
	@sudo update-grub
	@sudo shutdown -r now

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
	@sudo update-grub
	@sudo shutdown -r now
