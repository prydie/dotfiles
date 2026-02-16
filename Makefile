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
