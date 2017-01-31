[[ $TMUX = "" ]] && export TERM="xterm-256color"

if [ ! -f ~/.zshrc.zwc -o ~/.zshrc -nt ~/.zshrc.zwc ]; then
    zcompile ~/.zshrc
fi

#####################################################################
# powerlevel9k settings
#####################################################################

POWERLEVEL9K_MODE='awesome-fontconfig'
POWERLEVEL9K_LEFT_PROMPT_ELEMENTS=(context dir virtualenv vcs)
POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS=(status time)
POWERLEVEL9K_MODE='flat'
POWERLEVEL9K_NODE_VERSION_BACKGROUND="red"
POWERLEVEL9K_NODE_VERSION_FOREGROUND="white"
POWERLEVEL9K_SHORTEN_DIR_LENGTH=1
POWERLEVEL9K_SHORTEN_DELIMITER=""
POWERLEVEL9K_SHORTEN_STRATEGY="truncate_from_right"

#####################################################################
# zplug
#####################################################################

# Install zplug if not installed
[[ -d ~/.zplug ]] || {
  git clone https://github.com/zplug/zplug ~/.zplug
  source ~/.zplug/init.zsh
  zplug update --self
}

source ~/.zplug/init.zsh

zplug "zsh-users/zsh-syntax-highlighting", defer:2
zplug "zsh-users/zsh-history-substring-search"
zplug "zsh-users/zsh-autosuggestions", defer:3

# Completions
zplug "zsh-users/zsh-completions"
zplug "plugins/pass", from:oh-my-zsh

#  Aliases
zplug "plugins/common-aliases", from:oh-my-zsh
zplug "plugins/git", from:oh-my-zsh

# Themes
zplug "bhilburn/powerlevel9k", use:powerlevel9k.zsh-theme

if ! zplug check --verbose; then
  printf "Install? [y/N]: "
  if read -q; then
    echo; zplug install
  fi
fi

zplug load

#####################################################################
# environment
#####################################################################

DEFAULT_USER="andrew"

# allow group write
umask 002

# enable emacs key bindings for ^A / ^E
bindkey -e

export LANG=en_GB.UTF-8
export EDITOR='nvim'

export LESS='--tabs=4 --no-init --LONG-PROMPT --ignore-case --quit-if-one-screen --RAW-CONTROL-CHARS'

export HISTFILE=~/.zsh_history
export SAVEHIST=10000

#####################################################################
# Python
#####################################################################

export WORKON_HOME=$HOME/.virtualenvs

wrapper_path=$(which virtualenvwrapper.sh)
if [ -f  "$wrapper_path" ] ; then
    source virtualenvwrapper.sh
fi

#####################################################################
# Functions
#####################################################################

rsa-fingerprint() {
    openssl rsa -pubout -outform DER -in $1 2> /dev/null | openssl md5 -c
}

nexus() {
    sudo service openvpn@nexus $1
}

# Check if we can read given files and source those we can.
xsource() {
    if (( ${#argv} < 1 )) ; then
        printf 'usage: xsource FILE(s)...\n' >&2
        return 1
    fi

    while (( ${#argv} > 0 )) ; do
        [[ -r "$1" ]] && source "$1"
        shift
    done
    return 0
}

# Adds a new directory at the END of $PATH checking whether it exists or not
pathadd_end() {
    if [ -d "$1" ] && [[ ":$PATH:" != *":$1:"* ]]; then
        PATH="${PATH:+"$PATH:"}$1"
    fi
}

# Adds a new directory at the FRONT of $PATH checking whether it exists or not
pathadd_front() {
    if [ -d "$1" ] && [[ ":$PATH:" != *":$1:"* ]]; then
        PATH="$1${PATH:+":$PATH"}"
    fi
}

alias clipboard="perl -pe 'chomp if eof' | xclip -sel clip"

#####################################################################
# Go
#####################################################################

export GOPATH=$HOME/Projects/go
pathadd_end "$GOPATH/bin"

#####################################################################
# GPG
#####################################################################

# Sets up gpg-agent automatically for every shell
if [ -f ~/.gnupg/.gpg-agent-info ] && [ -n "$(pgrep gpg-agent)" ]; then
    source ~/.gnupg/.gpg-agent-info
    export GPG_AGENT_INFO
else
    eval $(gpg-agent --daemon --write-env-file ~/.gnupg/.gpg-agent-info)
fi

#####################################################################
# fzf
#####################################################################

export FZF_TMUX=1
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

#####################################################################
# Local overrides
#####################################################################

xsource $HOME/.zshrc.local
