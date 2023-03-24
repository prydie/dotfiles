export GOPATH=${HOME}/go

# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.

if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# zmodload zsh/zprof

[[ $TMUX = "" ]] && export TERM="xterm-256color"

source ~/.zplug/init.zsh

export POWERLEVEL9K_MODE='nerdfont-complete'

zplug "zsh-users/zsh-syntax-highlighting", defer:2
zplug "zsh-users/zsh-completions"

export NVM_LAZY_LOAD=true
export NVM_COMPLETION=true
zplug "lukechilds/zsh-nvm"

# zplug "junegunn/fzf-bin", as:command, from:gh-r, rename-to:fzf, use:"*${(L)$(uname -s)}*amd64*"
zplug "junegunn/fzf", as:command, use:bin/fzf-tmux

zplug "plugins/vi-mode",   from:oh-my-zsh

# Prompt
zplug mafredri/zsh-async, from:github
zplug romkatv/powerlevel10k, as:theme, depth:1
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

# FZF
#####
export FZF_DEFAULT_COMMAND='ag -l -g ""'
export FZF_DEFAULT_OPTS='--height 40% --reverse --border'


# kube
######
autoload -U colors; colors
source "${HOME}/.kube-ps1.sh"
RPROMPT='$()'
function custom_rprompt() {
    kube_ps1
}

[ -f ~/.zshrc.local ] && source ~/.zshrc.local

# zprof

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh
