#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset

function print_banner() {
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
}

# Globals
# -------

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd )"
platform=$(uname)
NVIM_DIR="${HOME}/.config/nvim"

# Utilities
# ---------

function print_error() {
  # Print output in red
  printf "\e[0;31m  [✖] $1 \e[0m\n"
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
  if [ "${YES_MODE}" -eq 1 ]; then
    return
  fi

  [[ "${REPLY}" =~ ^[Yy]$ ]] \
    && return 0 \
    || return 1
}

function ask_for_confirmation() {
  if [ "${YES_MODE}" -eq 1 ]; then
    return
  fi

  print_question "$1 (y/n) "
  while true; do
    read yn
    case ${yn} in
      [Yy]* ) break;;
      [Nn]* ) exit;;
      * ) print_question "$1 (y/n) ";;

    esac
  done
}

function symlink_dotfile() {
    local source_file="${__dir}/$1"
    local target_file="${HOME}/$2"

    if [ ! -e "${target_file}" ]; then
      execute "ln -fs ${source_file} ${target_file}" \
        "${target_file} → ${source_file}"
    elif [ "$(readlink "${target_file}")" == "${source_file}" ]; then
      print_success "${target_file} → ${source_file}"
    else
      ask_for_confirmation "'${target_file}' already exists, do you want to overwrite it?"
      if [ answer_is_yes ]; then
        rm -rf "${target_file}"
        execute "ln -fs ${source_file} ${target_file}" "${target_file} → ${source_file}"
      else
        print_error "${target_file} → ${source_file}"
      fi
    fi
}


# Opts.
# -----

# Set to 1 using -y flag. Suppresses all prompts.
YES_MODE=0

while getopts 'yv' flag; do
  case "${flag}" in
    y) YES_MODE=1 ;;
    v) set -x ;;
    *) print_error "Unexpected option ${flag}" ;;
  esac
done

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

function zsh_install() {
  # Test to see if Zsh is installed.  If it is:
  if [ -x "$(command -v "zsh")" ]; then
    print_success "Zsh already installed"
  else
    if [[ "${platform}" == "Linux" ]]; then
      execute "sudo apt-get install -y zsh" "Installing Zsh"
    elif [[ "${platform}" == "Darwin" ]]; then
      execute "brew install zsh" "Installed ZSH"
    fi
  fi
}

function zsh_setup() {
  print_info "Installing Zsh..."

  zsh_install
}

# Neovim
# ------

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
  if [ "$(command -v "nvim")" ]; then
    print_success "Neovim installed"
    return
  else
    if [[ "${platform}" == "Linux" ]]; then
      execute "sudo apt-get install -y software-properties-common" \
        "Installing software-properties-common"
      execute "sudo add-apt-repository ppa:neovim-ppa/unstable -y" \
        "Adding neovim PPA"
      sudo apt-get update &> /dev/null
      execute "sudo apt-get install -y neovim" "Installed neovim"
    elif [[ ${platform} == "Darwin" ]]; then
      execute "brew install neovim/neovim/neovim" "brew installing neovim"
      neovim_install
    fi
  fi
}

function neovim_setup() {
  print_info "Installing neovim..."

  neovim_install

  mkdir -p ${NVIM_DIR}/{backup,undo,swap}_files &> /dev/null
  print_result $? "Creating neovim dirs"

  # Enstall neovim python providers
  execute "pip2 install --user --upgrade neovim" "Install neovim (py2)"
  execute "pip3 install --user --upgrade neovim" "Install neovim (py3)"
  execute "sudo gem install neovim" "Install neovim (ruby gem)"

  neovim_install_checkers

  symlink_dotfile ".config/nvim/init.vim" ".config/nvim/init.vim"

  # Bootstrap neovim. We blindly say we've been successful as
  set +o errexit
  nvim +PlugInstall +qall &> /dev/null
  nvim +GoInstallBinaries +qall &> /dev/null
  nvim -es '+CheckHealth' '+w healthcheck.log' '+qa!' &> /dev/null
  set -o errexit

  local healthcheck_warnings=$(cat ${__dir}/healthcheck.log | grep -o WARNING | wc -l)

  # We accept 1 WARNING as in CI it's the system clipboard
  if [ "${healthcheck_warnings}" -gt 1 ]; then
    print_error "Git healthcheck failed. See ${__dir}/healthcheck.log for details."
  else
    print_success "Installed neovim plugins. CheckHealth passed."
    rm "${__dir}/healthcheck.log"
  fi
}

function symlink_dotfiles() {
  print_info "Symlinking dotfiles..."

  execute "mkdir -p $HOME/.config/powerline/themes" "mkdir ~/.config/powerline/themes"
  symlink_dotfile ".config/powerline/themes/powerline.json" ".config/powerline/themes/powerline.json"
  symlink_dotfile ".gitconfig" ".gitconfig"
  symlink_dotfile ".gitignore" ".gitignore"
  symlink_dotfile ".tmux.conf" ".tmux.conf"
  symlink_dotfile ".zshrc" ".zshrc"
  symlink_dotfile ".editorconfig" ".editorconfig"
}

function fonts_install() {
  if [[ "${platform}" == "Linux" ]]; then
    local fonts_dir="${HOME}/.fonts/"
  elif [[ "${platform}" == "Darwin" ]]; then
    local fonts_dir="$HOME/Library/Fonts/"
  fi

  mkd "${fonts_dir}"
  execute "cp .fonts/SourceCodePro+Powerline+Awesome+Regular.ttf ${fonts_dir}" \
    "Installed Source Code Pro Powerline Awesome"
}

function main () {
  print_banner

  ask_for_confirmation "Warning: this will overwrite your current dotfiles. Continue?"
  if [ ! answer_is_yes ]; then
    exit
  fi

  python_setup
  zsh_setup
  neovim_setup
  symlink_dotfiles
  fonts_install
}

main
