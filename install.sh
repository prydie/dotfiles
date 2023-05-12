#!/usr/bin/env bash

set -e -u -o pipefail

IFS=$'\n\t'

# Bootsrap with RCM
sudo apt install rcm  # TODO(apryde) yum

# Make it our own
make up -k 2>&1 | tee build.log

git config pull.ff only       # fast-forward only
