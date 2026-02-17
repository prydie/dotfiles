typeset -U path
path=("$HOME/.local/bin" "$HOME/bin" "$HOME/go/bin" "/opt/nvim-linux-x86_64/bin" $path)
export PATH
export GOPATH=${HOME}/go

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


# pyenv
#######
#
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && path=("$PYENV_ROOT/bin" $path)
if command -v pyenv >/dev/null 2>&1; then
  eval "$(pyenv init -)"
fi

[ -f ~/.zshrc.local ] && source ~/.zshrc.local

# zprof
