[[ $TMUX = "" ]] && export TERM="xterm-256color"

unamestr=`uname`

export ZSH=$HOME/.oh-my-zsh

ZSH_THEME="powerlevel9k/powerlevel9k"
POWERLEVEL9K_MODE='awesome-fontconfig'
POWERLEVEL9K_LEFT_PROMPT_ELEMENTS=(context dir virtualenv vcs)
POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS=(status time)

DEFAULT_USER="andrew"

plugins=(git vagrant httpie python pip tmux npm gulp virtualenv)

source $ZSH/oh-my-zsh.sh

# allow group write
umask 002

export LANG=en_GB.UTF-8
export EDITOR='nvim'

# Compilation flags
# export ARCHFLAGS="-arch x86_64"

# ssh
# export SSH_KEY_PATH="~/.ssh/id_rsa"

# virtualenvs
export WORKON_HOME=$HOME/.virtualenvs

wrapper_path=$(which virtualenvwrapper.sh)
if [ -f  "$wrapper_path" ] ; then
    source virtualenvwrapper.sh
fi

alias clipboard="perl -pe 'chomp if eof' | xclip -sel clip"

nexus() {
    sudo service openvpn@nexus $1
}

# FZF
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# Go
export GOPATH=$HOME/Projects/go
export PATH=$PATH:$GOPATH/bin
