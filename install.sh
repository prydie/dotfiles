#!/usr/bin/env bash

set -e -u -o pipefail

IFS=$'\n\t'

# Bootsrap with RCM
sudo apt install rcm
export RCRC="${HOME}/.dotfiles/rcrc"

echo ```
# hint:   git config pull.rebase false  # merge (the default strategy)
# hint:   git config pull.rebase true   # rebas
# hint:   git config pull.ff only       # fast-forward only
```
sudo snap install --edge starship

git config pull.ff only       # fast-forward only

# Make it our own
make install -k 2>&1 | tee build.log

sudo apt autoremove -y
sudo apt autoremove clean
