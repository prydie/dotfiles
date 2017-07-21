# Prydie's dotfiles

A not particularly well thought through collection of dotfiles.

## Tools of the trade

 - [zsh][1]
 - [zplug][2]
 - [tmux][3]
 - [vim][4]

## Installation

 1. Install [`rcm`][7]
 2. `env RCRC=$HOME/.dotfiles/rcrc rcup`

## Additional requirements

There are a number of requirements I haven't bothered automating their
installation. These include:

 - `curl`
 - `git`
 - `npm`
 - `pip`
 - `python3`
 - `python`
 - `ruby`
 - `tmux`

### Mac OS X

 - Install homebrew:
   `/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"`
 - Install pip https://pip.pypa.io/en/stable/installing/

## Inspiration / plagiarism

As with dotfiles everywhere I've begged, borrowed, and stolen snippets from too
many places to provide a comprehensive list here. Some more notable sources are
listed below:

 - [nicksp/dotfiles][5]
 - [thoughtbot/dotfiles][6]

[1]: http://zsh.sourceforge.net/
[2]: https://github.com/zplug/zplug
[3]: https://tmux.github.io/
[4]: http://www.vim.org/
[5]: https://github.com/nicksp/dotfiles
[6]: https://github.com/thoughtbot/dotfiles
[7]: https://github.com/thoughtbot/rcm
