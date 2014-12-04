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

" UI Modules
Bundle 'scrooloose/nerdtree'
Bundle 'kien/ctrlp.vim'
Bundle 'Valloric/YouCompleteMe'
Bundle 'rking/ag.vim'
Bundle 'tpope/vim-dispatch'

" UI Enhancements
Bundle 'altercation/vim-colors-solarized'
Bundle 'airblade/vim-gitgutter'
Bundle 'Lokaltog/powerline'

" Misc Bundles
Bundle 'scrooloose/nerdcommenter'
Bundle 'scrooloose/syntastic'

" Lang: Go
Bundle 'jnwhiteh/vim-golang'
Bundle 'fatih/vim-go'

" Lang: Coffescript
Bundle 'kchmck/vim-coffee-script'

if iCanHazVundle == 0
    echo "Installing Bundles, please ignore key map error messages"
    echo ""
    :BundleInstall
endif

" Setting up Vundle - the vim plugin bundler end

syntax on
syntax enable
set number
set smarttab
set expandtab
set colorcolumn=80
set background=dark
colorscheme solarized
let g:solarized_termtrans = 1
let g:solarized_termcolors= 256
set shiftwidth=4
set softtabstop=4
set autoindent
set tabstop=4

if $COLORTERM == 'gnome-terminal'
  set t_Co=256
else
  set t_Co=16
endif

set guifont=Ubuntu\ Mono\ derivative\ Powerline\ 10

set backspace=indent,eol,start

"
" NERDTree
"
autocmd vimenter * NERDTree
autocmd VimEnter * wincmd p
autocmd bufenter * if (winnr("$") == 1 && exists("b:NERDTreeType") && b:NERDTreeType == "primary") | q | endif
let NERDTreeIgnore = ['\.pyc$']
map <C-n> :NERDTreeToggle<CR>
autocmd BufNew * wincmd l

"
" Powerline

set rtp+=~/.vim/bundle/powerline/powerline/bindings/vim
set guifont=Ubuntu\ Mono\ derivative\ Powerline\ 12

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
nnoremap <leader>g :YcmCompleter GoToDefinitionElseDeclaration<CR>

"
" Syntastic
"

let g:syntastic_javascript_checkers = ['jshint']
let g:syntastic_python_checkers=['flake8']

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
