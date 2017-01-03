[[ $TMUX = "" ]] && export TERM="xterm-256color"

unamestr=$(uname)

# powerlevel9k settings
POWERLEVEL9K_MODE='awesome-fontconfig'
POWERLEVEL9K_LEFT_PROMPT_ELEMENTS=(context dir virtualenv vcs)
POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS=(status time)
POWERLEVEL9K_MODE='flat'

source $HOME/antigen.zsh

# Load the oh-my-zsh's library
antigen use oh-my-zsh

antigen bundles <<EOBUNDLES
vagrant
command-not-found
colored-man-pages
git
httpie
pass
python
pip
tmux
npm
gulp
virtualenv
zsh-users/zsh-syntax-highlighting
zsh-users/zsh-autosuggestions
zsh-users/zsh-completions
EOBUNDLES



# Load the theme
antigen theme bhilburn/powerlevel9k powerlevel9k

# Tell antigen that you're done
antigen apply

DEFAULT_USER="andrew"

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
pathadd() {
    if [ -d "$1" ] && [[ ":$PATH:" != *":$1:"* ]]; then
        PATH="${PATH:+"$PATH:"}$1"
    fi
}

# FZF
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# Go
export GOPATH=$HOME/Projects/go
pathadd "$GOPATH/bin"

xsource $HOME/.zshrc.local
