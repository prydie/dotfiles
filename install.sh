#!/usr/bin/env bash

set -e -u -o pipefail

IFS=$'\n\t'

make install -k 2>&1 | tee build.log
