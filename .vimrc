filetype plugin indent on

" Setting up Vundle - the vim plugin bundler

let iCanHazVundle=1
let vundle_readme=expand('~/.vim/bundle/vundle/README.md')
if !filereadable(vundle_readme)
    echo "Installing Vundle.."
    echo ""
    silent !mkdir -p ~/.vim/bundle
    silent !git clone https://github.com/gmarik/vundle ~/.vim/bundle/vundle
    let iCanHazVundle=0
endif
set rtp+=~/.vim/bundle/vundle/
call vundle#rc()
Bundle 'gmarik/vundle'

" Text processors
Bundle 'tell-k/vim-autopep8'
Bundle 'bronson/vim-trailing-whitespace'
Bundle 'tpope/vim-jdaddy'

" UI Modules
Bundle 'scrooloose/nerdtree'
Bundle 'kien/ctrlp.vim'
Bundle 'Valloric/YouCompleteMe'
Bundle 'rking/ag.vim'
Bundle 'tpope/vim-dispatch'
Bundle 'majutsushi/tagbar'

" UI Enhancements
Bundle 'altercation/vim-colors-solarized'
Bundle 'airblade/vim-gitgutter'
Bundle 'Lokaltog/powerline'
Bundle 'Yggdroot/indentLine'

" Misc Bundles
Bundle 'scrooloose/nerdcommenter'
Bundle 'scrooloose/syntastic'

" Lang: Go
Bundle 'fatih/vim-go'

" Lang: Coffescript
Bundle 'kchmck/vim-coffee-script'

" Lang: Python
Bundle 'klen/python-mode'


if iCanHazVundle == 0
    echo "Installing Bundles, please ignore key map error messages" echo ""
    :BundleInstall
endif

" Setting up Vundle - the vim plugin bundler end

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
let g:solarized_termtrans = 1
let g:solarized_termcolors= 256

if $COLORTERM == 'gnome-terminal'
  set t_Co=256
else
  set t_Co=16
endif

set backspace=indent,eol,start

" Mouse scrolling
set mouse=a

"
" NERDTree
"
autocmd vimenter * NERDTree
autocmd VimEnter * wincmd p
autocmd bufenter * if (winnr("$") == 1 && exists("b:NERDTreeType") && b:NERDTreeType == "primary") | q | endif
let NERDTreeIgnore = ['\.pyc$', '__pycache__']
map <C-n> :NERDTreeToggle<CR>
autocmd BufNew * wincmd l

"
" Powerline

set rtp+=~/.vim/bundle/powerline/powerline/bindings/vim
set guifont=Ubuntu\ Mono\ derivative\ Powerline\ 13

"
" Ctrl-P
"

let g:ctrlp_custom_ignore = {
  \ 'dir':  '\v[\/]\.(git|hg|svn)$',
  \ 'file': '\v\.(exe|so|dll|pyc)$',
  \ 'link': 'some_bad_symbolic_links',
  \ }

if executable('ag')
  " Use ag in CtrlP for listing files. Lightning fast and respects .gitignore
  let g:ctrlp_user_command = 'ag %s -l --nocolor -g ""'

  " ag is fast enough that CtrlP doesn't need to cache
  let g:ctrlp_use_caching = 0
endif

"
" The Silver Searcher (ag)
"
nnoremap K :Ag! "\b<cword>\b"<CR>:cw<CR>

"
" YCM
"

let g:ycm_autoclose_preview_window_after_completion=1
let g:ycm_collect_identifiers_from_tags_files = 1       " Let YCM read tags from Ctags file
let g:ycm_use_ultisnips_completer = 1                   " Default 1, just ensure
let g:ycm_seed_identifiers_with_syntax = 1              " Completion for programming language's keyword
let g:ycm_complete_in_comments = 1                      " Completion in comments
let g:ycm_complete_in_strings = 1                       " Completion in string
nnoremap <leader>g :YcmCompleter GoToDefinitionElseDeclaration<CR>

"
" Syntastic
"

let g:syntastic_javascript_checkers = ['jshint']
let g:syntastic_python_checkers=['flake8']

"
" Pymode
"
let g:pymode_folding = 0


"
" Powerline
"

let g:powerline_config_overrides={"common":{"log_file":"/tmp/powerline.log"}}

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
