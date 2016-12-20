#!/usr/bin/env bash

printf "\e[38;5;87m"
cat << "EOF"

  ██████╗ ██████╗ ██╗   ██╗██████╗ ██╗███████╗███████╗       ███████╗██╗██╗     ███████╗███████╗
  ██╔══██╗██╔══██╗╚██╗ ██╔╝██╔══██╗██║██╔════╝██╔════╝       ██╔════╝██║██║     ██╔════╝██╔════╝
  ██████╔╝██████╔╝ ╚████╔╝ ██║  ██║██║█████╗  ███████╗       █████╗  ██║██║     █████╗  ███████╗
  ██╔═══╝ ██╔══██╗  ╚██╔╝  ██║  ██║██║██╔══╝  ╚════██║       ██╔══╝  ██║██║     ██╔══╝  ╚════██║
  ██║     ██║  ██║   ██║   ██████╔╝██║███████╗███████║    ██╗██║     ██║███████╗███████╗███████║
  ╚═╝     ╚═╝  ╚═╝   ╚═╝   ╚═════╝ ╚═╝╚══════╝╚══════╝    ╚═╝╚═╝     ╚═╝╚══════╝╚══════╝╚══════╝
█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗
╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝
EOF
printf "\e[0m"

# Get the dotfiles directory's absolute path
DOTFILES_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Some useful general vars
platform=$(uname)
USER_SHELL=$(getent passwd $LOGNAME | cut -d: -f7)

# Neovim vars
NVIM_DIR="$HOME/.config/nvim"

# Zsh vars
OH_MY_ZSH_DIR=$HOME/.oh-my-zsh/

# Folders created inside $NVIM_DIR
declare -a NVIM_DIRS=(
)

# Utilities
# ---------

function print_error() {
  # Print output in red
  printf "\e[0;31m  [✖] $1 $2\e[0m\n"
}

function print_question() {
  # Print output in yellow
  printf "\e[0;33m  [?] $1\e[0m"
}

function print_info() {
  # Print output in purple
  printf "\n\e[0;35m $1\e[0m\n\n"
}

function print_success() {
  # Print output in green
  printf "\e[0;32m  [✔] $1\e[0m\n"
}

function print_result() {
  [ $1 -eq 0 ] \
    && print_success "$2" \
    || print_error "$2"

  [ "$3" == "true" ] && [ $1 -ne 0 ] \
    && exit
}

function execute() {
  $1 &> /dev/null
  print_result $? "${2:-$1}"
}

function mkd() {
  if [ -n "$1" ]; then
    if [ -e "$1" ]; then
      if [ ! -d "$1" ]; then
        print_info "$1 - a file with the same name already exists!"
      else
        print_success "Creating $1"
      fi
    else
      execute "mkdir -p $1" "$1"
    fi
  fi
}

function answer_is_yes() {
  [[ "$REPLY" =~ ^[Yy]$ ]] \
    && return 0 \
    || return 1
}

function ask_for_confirmation() {
  print_question "$1 (y/n) "
  while true; do
    read yn
    case $yn in
      [Yy]* ) break;;
      [Nn]* ) exit;;
      * ) print_question "$1 (y/n) ";;

    esac
  done
}

function symlink_dotfile() {
    local source_file="$DOTFILES_DIR/$1"
    local target_file="$HOME/$2"

    if [ ! -e "$target_file" ]; then
      execute "ln -fs $source_file $target_file" "$target_file → $source_file"
    elif [ "$(readlink "$target_file")" == "$source_file" ]; then
      print_success "$target_file → $source_file"
    else
      ask_for_confirmation "'$target_file' already exists, do you want to overwrite it?"
      if answer_is_yes; then
        rm -rf "$target_file"
        execute "ln -fs $source_file $target_file" "$target_file → $source_file"
      else
        print_error "$target_file → $source_file"
      fi
    fi
}

# Python
# ------

function python_install_venv() {
  execute "pip install --user virtualenv virtualenvwrapper" \
    "Installing virtualenv(wrapper)"
}

function python_setup() {
  print_info "Installing Python dependencies..."
  python_install_venv
}

# Zsh
# ---

function powerlevel9k_install() {
  local target=$OH_MY_ZSH_DIR/custom/themes/powerlevel9k
  if [[ -d $target ]]; then
    print_success "powerlevel9k installed"
  else
    execute "git clone https://github.com/bhilburn/powerlevel9k.git $target" \
      "Cloning powerlevel9k"
  fi
}

function oh_my_zsh_install() {
  # Install Oh My Zsh if it isn't already present
  if [[ ! -d $HOME/.oh-my-zsh/ ]]; then
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"
    oh_my_zsh_install
  else
    print_success "Oh My Zsh installed"
  fi
}

function zsh_install() {
  # Test to see if Zsh is installed.  If it is:
  if [ -f /bin/zsh -o -f /usr/bin/zsh ]; then
    print_success "Zsh installed"
    return
  else
    # If the platform is Linux, try an apt-get to install zsh and then recurse
    if [[ $platform == 'Linux' ]]; then
      sudo apt-get install zsh
      zsh_install
    # If the platform is OS X, tell the user to install zsh :)
    elif [[ $platform == 'Darwin' ]]; then
      echo "We'll install zsh, then re-run this script!"
      brew install zsh
      exit
    fi
  fi
}

function zsh_set_as_default_shell() {
  # Set the default shell to zsh if it isn't currently set to zsh
  if [[ $(echo $USER_SHELL) == $(which zsh) ]]; then
    print_success "Zsh set as default shell"
  else
    chsh -s $(which zsh)
    zsh_set_as_default_shell
  fi
}

function zsh_setup() {
  print_info "Installing Zsh..."

  powerlevel9k_install
  oh_my_zsh_install
  zsh_set_as_default_shell
  zsh_install
}

# Neovim
# ------

# TODO
#  - Install linters
#  - Run :PlugInstall?
#  - run :GoInstallBinaries?

function neovim_mkdirs() {
  for d in ${NVIM_DIRS[@]}; do
    mkd "$NVIM_DIR/$d"
  done
}

function neovim_install_python_hosts() {
  local venvs_dir="$NVIM_DIR/virtualenvs"

  mkd "$venvs_dir"

  local neopy2="$venvs_dir/neovim2"
  local neopy3="$venvs_dir/neovim3"

  if [ ! -d "$neopy2" ]; then
    execute "virtualenv $neopy2 --python=python2" "Creating neovim py2 venv"
    execute "$neopy2/bin/pip install neovim" "Installing neovim (pip2)"
  else
    print_success "Neovim py2 venv installed"
  fi
  if [ ! -d "$neopy3" ]; then
    execute "virtualenv $neopy3 --python=python3" "Creating neovim py3 env"
    execute "$neopy2/bin/pip install neovim" "Installing neovim (pip3)"
  else
    print_success "Neovim py3 venv installed"
  fi
}

function neovim_install_checkers() {
  if [ ! -x "$(command -v "flake8")" ]; then
    execute "pip install --user flake8" "Installing flake8"
  else
    print_success "fake8 installed"
  fi
  if [ ! -x "$(command -v "eslint")" ]; then
    execute "sudo npm install -g eslint" "Installing eslint"
  else
    print_success "eslint installed"
  fi
}

function neovim_install() {
  if [ -f /bin/nvim -o -f /usr/bin/nvim ]; then
    print_success "Neovim installed"
    return
  else
    if [[ $platform == 'Linux' ]]; then
      execute "sudo apt-get install software-properties-common" \
        "Installing software-properties-common"
      execute "sudo add-apt-repository ppa:neovim-ppa/unstable" \
        "Adding neovim PPA"
      execute "sudo apt-get update" "apt update"
      execute "sudo apt-get install neovim" "apt install neovim"
    elif [[ $platform == 'Darwin' ]]; then
      execute "brew install neovim/neovim/neovim" "brew installing neovim"
    fi
  fi
  neovim_install
}

function neovim_setup() {
  print_info "Installing neovim..."

  neovim_install
  mkdir -p $NVIM_DIR/{backup,undo,swap}_files &> /dev/null
  print_result $? "Creating neovim dirs"

  neovim_install_python_hosts
  neovim_install_checkers
}

function symlink_dotfiles() {
  print_info "Symlinking dotfiles..."

  symlink_dotfile ".config/init.vim" ".config/init.vim"
  symlink_dotfile ".gitconfig" ".gitconfig"
  symlink_dotfile ".gitignore" ".gitignore"
  symlink_dotfile ".tmux.conf" ".tmux.conf"
  symlink_dotfile ".zshrc" ".zshrc"
  symlink_dotfile ".editorconfig" ".editorconfig"
}

function main () {
  ask_for_confirmation "Warning: this will overwrite your current dotfiles. Continue?"
  if [ ! answer_is_yes ]; then
    exit
  fi

  python_setup
  zsh_setup
  neovim_setup
  symlink_dotfiles
}

main
