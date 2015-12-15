set nocompatible              " be iMproved, required
filetype off                  " required

" set the runtime path to include Vundle and initialize
set rtp+=~/.vim/bundle/Vundle.vim
call vundle#begin()

" let Vundle manage Vundle, required
Plugin 'VundleVim/Vundle.vim'

" Text processors
Plugin 'bronson/vim-trailing-whitespace'
Plugin 'tpope/vim-jdaddy'

" UI Modules
Plugin 'scrooloose/nerdtree'
Plugin 'kien/ctrlp.vim'
Plugin 'Valloric/YouCompleteMe'
Plugin 'rking/ag.vim'
Plugin 'tpope/vim-dispatch'
Plugin 'majutsushi/tagbar'

" UI Enhancements
Plugin 'flazz/vim-colorschemes'
Plugin 'powerline/powerline', {'rtp': 'powerline/bindings/vim/'}
Plugin 'Yggdroot/indentLine'

" Misc Plugins
Plugin 'scrooloose/nerdcommenter'
Plugin 'scrooloose/syntastic'
Plugin 'ervandew/supertab'

" Git plugins
Plugin 'airblade/vim-gitgutter'
Plugin 'tpope/vim-fugitive'
Plugin 'Xuyuanp/nerdtree-git-plugin'

" Lang: Go
Plugin 'fatih/vim-go'

" Lang: Python
Plugin 'klen/python-mode'

"All of your Plugins must be added before the following line
call vundle#end()            " required
filetype plugin indent on    " required

syntax on
syntax enable
set number
set splitbelow
set splitright

set smarttab
set expandtab
set shiftwidth=4
set softtabstop=4
set autoindent
set tabstop=4

set colorcolumn=80

set background=dark
colorscheme solarized
let g:solarized_termcolors = 256
let g:solarized_termtrans = 1

set t_Co=16

set backspace=indent,eol,start

" Mouse scrolling
set mouse=a

"
" NERDTree
"

" open a NERDTree automatically when vim starts up if no files were specified
autocmd StdinReadPre * let s:std_in=1
autocmd VimEnter * if argc() == 0 && !exists("s:std_in") | NERDTree | endif

" close vim if the only window left open is a NERDTree
autocmd bufenter * if (winnr("$") == 1 && exists("b:NERDTree") && b:NERDTree.isTabTree()) | q | endif

let NERDTreeIgnore = ['\.pyc$', '__pycache__']

map <C-n> :NERDTreeToggle<CR>

autocmd BufNew * wincmd l

set guifont=Source\ Code\ Pro\ for\ Powerline\ Light

"
" Ctrl-P
"
let g:ctrlp_custom_ignore = {
  \ 'dir':  '\v[\/]\.(git|hg|svn)$',
  \ 'file': '\v\.(exe|so|dll|pyc)$',
  \ }

"
" The Silver Searcher (ag)
"
if executable('ag')
  " Use ag in CtrlP for listing files. Lightning fast and respects .gitignore
  let g:ctrlp_user_command = 'ag %s -l --nocolor -g ""'

  " ag is fast enough that CtrlP doesn't need to cache
  let g:ctrlp_use_caching = 0
    nnoremap K :Ag! "\b<cword>\b"<CR>:cw<CR>
endif


"
" YCM
"
let g:ycm_autoclose_preview_window_after_completion=1
let g:ycm_seed_identifiers_with_syntax = 1              " Completion for programming language's keyword

let g:ycm_complete_in_comments = 1                      " Completion in comments
let g:ycm_complete_in_strings = 1                       " Completion in string

nnoremap <leader>g :YcmCompleter GoToDefinitionElseDeclaration<CR>

"
" Syntastic
"
let g:syntastic_javascript_checkers = ['jshint']
let g:syntastic_python_checkers=[]

"
" Pymode
"
let g:pymode_folding = 0


"
" Filetype spesific
"
autocmd Filetype py setlocal ts=4 sts=4 sw=4 et sta ai
autocmd Filetype cpp setlocal ts=2 sts=2 sw=2
autocmd Filetype yaml setlocal ts=2 sts=2 sw=2
autocmd Filetype go setlocal ts=4 sts=4 sw=4 et!

autocmd BufNewFile,BufReadPost *.go set filetype=go

"
" vim-go
"
let g:go_auto_type_info = 0
let g:go_fmt_command = "gofmt"
au FileType go nmap <Leader>e <Plug>(go-rename)
