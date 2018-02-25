[[ $TMUX = "" ]] && export TERM="xterm-256color"

source ~/.zplug/init.zsh

zplug "zsh-users/zsh-syntax-highlighting", defer:2
zplug "zsh-users/zsh-completions"

zplug "plugins/common-aliases", from:oh-my-zsh
zplug "plugins/git", from:oh-my-zsh

zplug "junegunn/fzf-bin", as:command, from:gh-r, rename-to:fzf, use:"*${(L)$(uname -s)}*amd64*"
zplug "junegunn/fzf", as:command, use:bin/fzf-tmux

# Prompt
zplug mafredri/zsh-async, from:github
zplug sindresorhus/pure, use:pure.zsh, from:github, as:theme

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


# Python
########

# Load virtualenvwrapper if present
_venvwrapper=$(which virtualenvwrapper.sh)
[[ -x "${_venvwrapper}" ]] && . "${_venvwrapper}"


# Aliases
#########

[[ -f ~/.aliases ]] && . ~/.aliases


# Completions
#############

fpath=(
  /usr/local/share/zsh-completions
  /usr/local/share/zsh/site-functions
  $fpath
)

if [ -x "$(command -v kubectl)" ]; then
    source <(kubectl completion zsh)
fi

if [ -x "$(command -v pipenv)" ]; then
    eval $(_PIPENV_COMPLETE=source-zsh pipenv)
fi

#if [ -x "$(command -v gopass)" ]; then
    #source <(gopass completion )
#fi

# FZF
#####
export FZF_DEFAULT_COMMAND='ag -l -g ""'
export FZF_DEFAULT_OPTS='--height 40% --reverse --border'


[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh
