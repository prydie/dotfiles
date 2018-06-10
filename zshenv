export PATH="${HOME}/.local/bin:${HOME}/.yarn/bin:${HOME}/.npm-global/bin:${PATH}"

# Go
####

export GOPATH="${HOME}/go"
export PATH="${GOPATH}/bin:${PATH}"

[[ -f ~/.zshenv.local ]] && source ~/.zshenv.local
