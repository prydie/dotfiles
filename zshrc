typeset -U path
path=("$HOME/.local/bin" "$HOME/bin" "$HOME/go/bin" "/opt/nvim-linux-x86_64/bin" $path)
export PATH
export GOPATH=${HOME}/go
export MISE_GLOBAL_CONFIG_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/mise/config.toml"
if [ ! -f "${MISE_GLOBAL_CONFIG_FILE}" ] && [ -f "$HOME/.dotfiles/config/mise/config.toml" ]; then
  export MISE_GLOBAL_CONFIG_FILE="$HOME/.dotfiles/config/mise/config.toml"
fi
export VALE_CONFIG_PATH="${XDG_CONFIG_HOME:-$HOME/.config}/vale/vale.ini"
if [ ! -f "${VALE_CONFIG_PATH}" ] && [ -f "$HOME/.dotfiles/config/vale/vale.ini" ]; then
  export VALE_CONFIG_PATH="$HOME/.dotfiles/config/vale/vale.ini"
fi
typeset -U fpath
fpath=("${XDG_DATA_HOME:-$HOME/.local/share}/zsh/site-functions" $fpath)

# zmodload zsh/zprof

source ~/.zplug/init.zsh

zplug "zsh-users/zsh-syntax-highlighting", defer:2
zplug "zsh-users/zsh-history-substring-search"
zplug "zsh-users/zsh-completions"

export NVM_LAZY_LOAD=true
export NVM_COMPLETION=true
zplug "lukechilds/zsh-nvm"

zplug "junegunn/fzf", as:command, use:bin/fzf-tmux

# Prompt
zplug mafredri/zsh-async, from:github

eval "$(starship init zsh)"

# Install plugins if there are plugins that have not been installed
if ! zplug check --verbose; then
  printf "Install? [y/N]: "
  if read -q; then
    echo; zplug install
  fi
fi

zplug load

# Environment
#############

bindkey -e  # emacs key bindings

# colors!
autoload -U colors
colors

if whence dircolors >/dev/null; then
  eval "$(dircolors ~/.dir_colors)"
  zstyle ':completion:*:default' list-colors ${(s.:.)LS_COLORS}
else
  export CLICOLOR=1
  zstyle ':completion:*:default' list-colors ''
fi

# alias ls="ls --color=auto"

# shut it!
setopt NO_BEEP

# editor
export VISUAL=nvim
export EDITOR=$VISUAL


# Command history
#################

if [ -z "$HISTFILE" ]; then
    HISTFILE=$HOME/.zsh_history
fi

HISTSIZE=10000
SAVEHIST=10000

alias history='fc -El 1'

setopt append_history
setopt extended_history
setopt hist_expire_dups_first
setopt hist_ignore_dups
setopt hist_ignore_space
setopt hist_verify
setopt inc_append_history
setopt share_history

# Aliases
#########

[[ -f ~/.aliases ]] && . ~/.aliases


# Completions
#############
autoload -Uz compinit
typeset -g __zcompcache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/zsh"
typeset -g __zcompdump="${__zcompcache_dir}/.zcompdump-${ZSH_VERSION}"
mkdir -p "${__zcompcache_dir}"
if ! (( ${+_comps} )); then
  compinit -d "${__zcompdump}"
fi
if (( ${+commands[kubectl]} )); then
  compdef _kubectl kubectl k
fi
zstyle ':completion:*' menu select
zstyle ':completion:*' matcher-list 'm:{a-z}={A-Za-z}'
zstyle ':completion:*' use-cache on
zstyle ':completion:*' cache-path "${__zcompcache_dir}/completion-cache"
zstyle ':completion:*:*:cd:*' ignored-patterns '*/.git' '*/node_modules' '*/.direnv'

# FZF
#####
export FZF_DEFAULT_COMMAND='fd --type f --hidden --follow --exclude .git'
export FZF_DEFAULT_OPTS='--height 40% --reverse --border'
if [ -f /usr/share/doc/fzf/examples/key-bindings.zsh ]; then
  source /usr/share/doc/fzf/examples/key-bindings.zsh
fi
if [ -f /usr/share/doc/fzf/examples/completion.zsh ]; then
  source /usr/share/doc/fzf/examples/completion.zsh
fi

if command -v atuin >/dev/null 2>&1; then
  eval "$(atuin init zsh --disable-up-arrow)"
fi

bindkey -M emacs '\ee' expand-history


# pyenv
#######
#
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && path=("$PYENV_ROOT/bin" $path)
if command -v pyenv >/dev/null 2>&1; then
  eval "$(pyenv init -)"
fi

if [ -x "$HOME/.local/bin/mise" ]; then
  eval "$("$HOME/.local/bin/mise" activate zsh)"
fi

[ -f ~/.zshrc.local ] && source ~/.zshrc.local

# zprof
