#!/usr/bin/env bash

set -e -u -o pipefail

IFS=$'\n\t'

# Bootsrap with RCM
sudo apt install rcm

# Make it our own
make install -k 2>&1 | tee build.log

git config pull.ff only       # fast-forward only

# Make it our own
make install -k 2>&1 | tee build.log
