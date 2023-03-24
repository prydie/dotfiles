#!/usr/bin/env bash

set -e -u -o pipefail

IFS=$'\n\t'

# Bootsrap with RCM
sudo apt install rcm

# Make it our own
make install -k 2>&1 | tee build.log

sudo apt autoremove clean
