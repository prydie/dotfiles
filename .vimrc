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
    "Add your bundles here
    Bundle 'scrooloose/nerdtree'
    Bundle 'scrooloose/nerdcommenter'
    Bundle 'scrooloose/syntastic'
    Bundle 'Lokaltog/powerline'
    Bundle 'kien/ctrlp.vim'
    Bundle 'altercation/vim-colors-solarized'
    Bundle 'EasyGrep'
    Bundle 'Valloric/YouCompleteMe'
    Bundle 'airblade/vim-gitgutter'
    Bundle 'Rykka/riv.vim'
    Bundle 'Rykka/clickable.vim'
    Bundle 'rking/ag.vim'
    Bundle 'jnwhiteh/vim-golang'
    Bundle 'bronson/vim-trailing-whitespace'
    Bundle 'klen/python-mode'
    Bundle 'kchmck/vim-coffee-script'
    Bundle 'fatih/vim-go'
    Bundle 'tell-k/vim-autopep8'
    Bundle 'tpope/vim-dispatch'
    "...All your other bundles...
    if iCanHazVundle == 0
        echo "Installing Bundles, please ignore key map error messages"
        echo ""
        :BundleInstall
    endif
" Setting up Vundle - the vim plugin bundler end

set number
set guifont=Ubuntu\ Mono\ derivative\ Powerline\ 10

syntax on
syntax enable
set backspace=indent,eol,start

set nofoldenable    " disable folding

if $COLORTERM == 'gnome-terminal'
    set t_Co=256
endif

set background=dark
colorscheme solarized

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
"

set rtp+=~/.vim/bundle/powerline/powerline/bindings/vim
set guifont=Ubuntu\ Mono\ derivative\ Powerline\ 12

"
" Python Spesific
"

set tabstop=4
set softtabstop=4
set shiftwidth=4
set textwidth=80
set smarttab
set expandtab
set colorcolumn=80

let g:syntastic_python_checkers=['flake8']

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
" YCM
"

let g:ycm_autoclose_preview_window_after_completion=1
nnoremap <leader>g :YcmCompleter GoToDefinitionElseDeclaration<CR>


"
" PyMode
"
let g:pymode_doc=0
let g:pymode_rope_lookup_project = 0
let g:pymode_rope_completion = 0


"
" EasyGrep
"

"let g:EasyGrepMode=2
"let g:EasyGrepFilesToExclude="node_modules,env"
"let g:EasyGrepRecursive=1
"let g:EasyGrepCommand=1

let g:syntastic_javascript_checkers = ['jshint']

"
" Powerline
"

let g:powerline_config_overrides={"common":{"log_file":"/tmp/powerline.log"}}

"
" Filetype spesific
"
autocmd Filetype cpp setlocal ts=2 sts=2 sw=2
autocmd BufNewFile,BufReadPost *.go set filetype=go
