#!/usr/bin/env bash

set -e -u -o pipefail

IFS=$'\n\t'

# Bootsrap with RCM
sudo apt install rcm

sudo snap install starship

```
hint:   git config pull.rebase false  # merge (the default strategy)
hint:   git config pull.rebase true   # rebase
hint:   git config pull.ff only       # fast-forward only
```

git config pull.ff only       # fast-forward only

# Make it our own
make install -k 2>&1 | tee build.log
