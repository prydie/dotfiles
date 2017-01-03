# Prydie's dotfiles

[![Build Status](https://travis-ci.org/prydie/dotfiles.svg?branch=master)](https://travis-ci.org/prydie/dotfiles)

A not particularly well thought through collection of dotfiles.

## Tools of the trade

 - [Zsh](http://zsh.sourceforge.net/)
 - [Oh my Zsh](https://github.com/robbyrussell/oh-my-zsh)
 - [tmux](https://tmux.github.io/)
 - [neovim](https://neovim.io/)

## Languages

 - Python
 - Golang
 - Misc. sysadmin

## Inspiration / plagiarism

As with dotfiles everywhere I've begged, borrowed, and stolen snippets from too
many places to provide a comprehensive list here. Some more notable sources are
listed below:

 - [nicksp/dotfiles](https://github.com/nicksp/dotfiles)
 - [gabrielelana/awesome-terminal-fonts](https://github.com/gabrielelana/awesome-terminal-fonts)
   for the Source Code Pro variant.

## Requirements

There are a number of requirements I haven't bothered automating their
installation. These include:

 - `git`
 - `tmux`
 - `curl`
 - `python`
 - `python3`
 - `python-pip`
 - `python3-pip`
 - `ruby`
 - `pip`
 - `npm` (`nodejs`)

 For a more complete list see the `DockerFile`.

### Mac OS X

There is no CI for OS X in place so installation is a little more involved,
however, it is tested.

Additional Steps:

 - Install homebrew: `/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"`
 - Install pip https://pip.pypa.io/en/stable/installing/
 - `brew install python3 tmux wget node`
