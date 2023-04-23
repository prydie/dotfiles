#!/usr/bin/env bash

# export HOME=$($pwd)

mkdir -p /usr/bin/

cd "${HOME}/.dotfiles" || exit

git config pull.ff only       # fast-forward only

make install -k 2>&1 | tee build.log

cd "${HOME}/.dotfiles/" || exit
