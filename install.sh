#!/usr/bin/env bash

set -euo pipefail

IFS=$'\n\t'

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This bootstrap script currently supports Debian/Ubuntu (apt-get) only."
  exit 1
fi

missing_pkgs=0
command -v git >/dev/null 2>&1 || missing_pkgs=1
command -v make >/dev/null 2>&1 || missing_pkgs=1
command -v rcup >/dev/null 2>&1 || missing_pkgs=1

if [ "${missing_pkgs}" -eq 1 ]; then
  echo "Installing bootstrap packages (git, make, rcm)..."
  sudo apt-get update
  sudo apt-get install -y git make rcm
fi

make up
git config pull.ff only
