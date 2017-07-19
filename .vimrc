" Autoinstall Plug

if empty(glob('~/.vim/autoload/plug.vim'))
  silent !curl -fLo ~/.vim/autoload/plug.vim --create-dirs
    \ https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim
  autocmd VimEnter * PlugInstall --sync | source $MYVIMRC
endif

call plug#begin('~/.vim/plugged')

" Sensible defaullts
Plug 'tpope/vim-sensible'

" Fuzzy File Finder
Plug 'junegunn/fzf', { 'dir': '~/.fzf', 'do': './install --all' }
Plug 'junegunn/fzf.vim'

" Language support
Plug 'fatih/vim-go', { 'do': ':GoInstallBinaries' }
Plug 'sheerun/vim-polyglot'
Plug 'fisadev/vim-isort'  " python import sorting

" Omnicomplete
function! BuildYCM(info)
  " info is a dictionary with 3 fields
  " - name:   name of the plugin
  " - status: 'installed', 'updated', or 'unchanged'
  " - force:  set on PlugInstall! or PlugUpdate!
  if a:info.status == 'installed' || a:info.force
    !./install.py --clang-completer --gocode-completer --tern-completer
  endif
endfunction

Plug 'Valloric/YouCompleteMe', { 'do': function('BuildYCM') }

" Linting
Plug 'w0rp/ale'

" Formatting
Plug 'editorconfig/editorconfig-vim'

" UI
Plug 'vim-airline/vim-airline'
Plug 'vim-airline/vim-airline-themes'

Plug 'scrooloose/nerdtree'
Plug 'ryanoasis/vim-devicons'

" Git
Plug 'tpope/vim-fugitive'
Plug 'airblade/vim-gitgutter'

" Text wrangling
Plug 'tpope/vim-surround'
Plug 'scrooloose/nerdcommenter'

" Themes
Plug 'lifepillar/vim-solarized8'

call plug#end()


" Basic config
""""""""""""""
set number              " Line numbers
set ignorecase!         " Ignore case in search
set hidden              " Hide instead of close bufffers to preserve history
set splitbelow          " Horizontal split below current.
set splitright          " Vertical split to right of current.
set vb                  " No error bells!
set colorcolumn=80      " Keep an eye on our line length.
set mouse=a             " Scoll vim not tmux!


" Mappings
""""""""""
map <C-n> :NERDTreeToggle<CR>


" Theme
"""""""
set termguicolors
let &t_8f = "\<Esc>[38;2;%lu;%lu;%lum"
let &t_8b = "\<Esc>[48;2;%lu;%lu;%lum"
colorscheme solarized8_dark


" Golang
""""""""
autocmd Filetype go setlocal nolist

" settings
let g:go_highlight_functions = 1
let g:go_highlight_methods = 1
let g:go_highlight_fields = 1
let g:go_highlight_types = 1
let g:go_highlight_operators = 1
let g:go_highlight_build_constraints = 1

" mappings
au FileType go nmap <leader>r <Plug>(go-run)
au FileType go nmap <leader>b <Plug>(go-build)
au FileType go nmap <leader>t <Plug>(go-test)
au FileType go nmap <leader>c <Plug>(go-coverage)


" FZF file finder plugin
""""""""""""""""""""""""
noremap <C-p> :FZF<CR>
let g:fzf_height = '30%'
let g:fzf_command_prefix = 'Fzf'
let g:fzf_tags_options = '-f .ctags"'
let $FZF_DEFAULT_COMMAND = 'ag -l -g ""'
let g:fzf_colors =
\ { 'fg':      ['fg', 'Normal'],
  \ 'bg':      ['bg', 'Normal'],
  \ 'hl':      ['fg', 'Comment'],
  \ 'fg+':     ['fg', 'CursorLine', 'CursorColumn', 'Normal'],
  \ 'bg+':     ['bg', 'CursorLine', 'CursorColumn'],
  \ 'hl+':     ['fg', 'Statement'],
  \ 'info':    ['fg', 'PreProc'],
  \ 'prompt':  ['fg', 'Conditional'],
  \ 'pointer': ['fg', 'Exception'],
  \ 'marker':  ['fg', 'Keyword'],
  \ 'spinner': ['fg', 'Label'],
  \ 'header':  ['fg', 'Comment'] }


" Airline configuration
"""""""""""""""""""""""
"let g:airline_powerline_fonts = 0
"let g:airline_symbols = {}

let g:airline_left_sep=''
let g:airline_right_sep=''

let g:airline_theme='papercolor'


" Ale linter
""""""""""""
let g:ale_set_loclist = 1
let g:ale_open_list = 1
let g:ale_lint_on_text_changed = 'never'
