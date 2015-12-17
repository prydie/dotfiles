call plug#begin()

Plug 'tpope/vim-sensible'
Plug 'Xuyuanp/nerdtree-git-plugin' | Plug 'scrooloose/nerdtree'

" Text processors
Plug 'bronson/vim-trailing-whitespace'
Plug 'tpope/vim-jdaddy'

" UI Modules
Plug 'Valloric/YouCompleteMe'
Plug 'junegunn/fzf', { 'dir': '~/.fzf', 'do': 'yes \| ./install' }
Plug 'tpope/vim-dispatch'
Plug 'majutsushi/tagbar'

" UI Enhancements
Plug 'flazz/vim-colorschemes'
Plug 'powerline/powerline', {'rtp': 'powerline/bindings/vim/'}
Plug 'Yggdroot/indentLine'

" Misc Plugs
Plug 'scrooloose/nerdcommenter'
Plug 'scrooloose/syntastic'
Plug 'ervandew/supertab'

" Git plugins
Plug 'airblade/vim-gitgutter'
Plug 'tpope/vim-fugitive'

" Lang: Go
Plug 'fatih/vim-go'

" Lang: Python
Plug 'davidhalter/jedi-vim', {'for': 'python'}

call plug#end()

"
" Colourscheme
"
set background=dark
colorscheme solarized
let g:solarized_termcolors = 256
let g:solarized_termtrans = 1

" Probably only needed on OS X (Terminal)
set t_Co=16

"
set ignorecase!

" Line numbers
set number

set splitbelow
set splitright

set expandtab
set shiftwidth=4
set softtabstop=4
set tabstop=4

" Remind us to keep it short and sweet
set colorcolumn=80

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

let NERDTreeIgnore = ['\.pyc$', '\.egg$', '\.o$', '\~$', '__pycache__$', '\.egg-info$']

map <C-n> :NERDTreeToggle<CR>

autocmd BufNew * wincmd l

set guifont=Source\ Code\ Pro\ for\ Powerline\ Light

"
" FZF
"

" Map main trigger for fuzzy file finder
noremap <C-p> :FZF<CR>

" Ignore .gitignore files when using ctrl-p
let $FZF_DEFAULT_COMMAND = 'ag -l -g ""'

" Set hight of FZF window
let g:fzf_height = '25%'

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
let g:syntastic_auto_jump = 0
let g:syntastic_check_on_open = 1
let g:syntastic_enable_signs = 1
let g:syntastic_error_symbol = "✗"
let g:syntastic_javascript_checkers = ['jshint']
let g:syntastic_python_checkers=['flake8']
let g:syntastic_warning_symbol = "⚠"

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
