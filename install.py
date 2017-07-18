#!/usr/bin/env python

"""
Dotfile Installer
-----------------
Installs dotfiles from the current directory to the current users home
directory.
"""

import errno
import logging
import os
import sys

logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')

DOTFILES = {
    '.vimrc': '.vimrc',
    'tmux/tmux.conf': '.tmux.conf',
    'zsh/.zshenv': '.zshenv',
    'zsh/.zshrc': '.zshrc',
    '.gitconfig': '.gitconfig'
}

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
HOME = os.path.expanduser('~')


def symlink_dotfile(src, dest):
    """Creates a dotfile symbolic link."""
    src = os.path.join(BASE_DIR, src)
    dest = os.path.join(HOME, dest)

    try:
        os.symlink(src, dest)
    except OSError as err:
        if err.errno == errno.EEXIST:
            os.remove(dest)
            logging.info("removed %s", dest)
            os.symlink(src, dest)
        else:
            logging.error("failed to symlink %s -> %s", dest, src)
            logging.exception(err)
    logging.info("symlinked %s -> %s", dest, src)


if __name__ == '__main__':
    for src, dest in DOTFILES.items():
        symlink_dotfile(src, dest)
