call plug#begin('~/.vim/plugged')

" Sensible defaullts
Plug 'tpope/vim-sensible'

" Misc
Plug 'tpope/vim-dispatch'
Plug 'ervandew/supertab'

" Finding things
Plug 'junegunn/fzf', { 'dir': '~/.fzf', 'do': './install --all' }
Plug 'junegunn/fzf.vim'
Plug 'mileszs/ack.vim'

" Language support
Plug 'fatih/vim-go', { 'do': ':GoInstallBinaries' }
Plug 'sheerun/vim-polyglot'
Plug 'pangloss/vim-javascript'
Plug 'hashivim/vim-terraform'

" Python import sorting
" NOTE: pip3 install --user isort
Plug 'fisadev/vim-isort'
Plug 'hdima/python-syntax', { 'for': 'python' }
Plug 'davidhalter/jedi-vim', { 'for': 'python' }

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

if has('nvim')
  Plug 'Shougo/deoplete.nvim', { 'do': ':UpdateRemotePlugins' }
  Plug 'nsf/gocode', { 'rtp': 'vim', 'do': '~/.vim/plugged/gocode/vim/symlink.sh' }
  Plug 'zchee/deoplete-go', { 'do': 'make'}
  Plug 'zchee/deoplete-jedi', { 'for': 'python' }
else
  Plug 'Valloric/YouCompleteMe', { 'do': function('BuildYCM') }
endif

Plug 'majutsushi/tagbar'

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
Plug 'tpope/vim-rhubarb'
Plug 'airblade/vim-gitgutter'

" Text wrangling
Plug 'tpope/vim-surround'
Plug 'scrooloose/nerdcommenter'

" Themes
Plug 'lifepillar/vim-solarized8'
Plug 'rakr/vim-one'

call plug#end()


" Basic config
""""""""""""""
set number                      " Line numbers
set ignorecase!                 " Ignore case in search
set hidden                      " Hide instead of close bufffers to preserve history
set splitbelow                  " Horizontal split below current.
set splitright                  " Vertical split to right of current.
set noerrorbells                " No error bells!
set colorcolumn=80              " Keep an eye on our line length.
set mouse=a                     " Scoll vim not tmux!
set modeline                    " Pickup conf from modeline comments.
set nobackup                    " No backup files
set noswapfile                  " No swap files
set completeopt+=noselect
set nocursorcolumn           " speed up syntax highlighting
set nocursorline
set updatetime=300
set pumheight=10             " Completion window max size
set diffopt+=vertical                    " Always use vertical diffs

" highlight
set list
set listchars=tab:»\ ,extends:›,precedes:‹,nbsp:·,trail:·

" Better split switching
map <C-j> <C-W>j
map <C-k> <C-W>k
map <C-h> <C-W>h
map <C-l> <C-W>l

" Clear search highlights
map <leader><Space> :nohlsearch<cr>

" If you prefer the Omni-Completion tip window to close when a selection is
" made, these lines close it on movement in insert mode or when leaving
" insert mode
autocmd CursorMovedI * if pumvisible() == 0|pclose|endif
autocmd InsertLeave * if pumvisible() == 0|pclose|endif


" Theme
"""""""
set termguicolors
let &t_8f = "\<Esc>[38;2;%lu;%lu;%lum"
let &t_8b = "\<Esc>[48;2;%lu;%lu;%lum"
set background=dark
:silent! colorscheme one
let g:one_allow_italics = 1
if !has('gui_running')
  set t_Co=256
endif

" NERDTree
""""""""""
map <C-n> :NERDTreeToggle<CR>
autocmd FileType nerdtree setlocal nolist
let NERDTreeIgnore = ['\.pyc$']


" git commit
""""""""""""
autocmd Filetype gitcommit setlocal cc=72
autocmd Filetype gitcommit setlocal spell


" Golang
""""""""
autocmd Filetype go setlocal nolist
autocmd BufNewFile,BufRead *.go setlocal noexpandtab tabstop=4 shiftwidth=4

" settings
let g:go_echo_go_info = 0
let g:go_fmt_command = "goimports"
let g:go_highlight_functions = 1
let g:go_highlight_methods = 1
let g:go_highlight_fields = 1
let g:go_highlight_types = 1
let g:go_highlight_operators = 1
let g:go_highlight_build_constraints = 1

" run :GoBuild or :GoTestCompile based on the go file
function! s:build_go_files()
  let l:file = expand('%')
  if l:file =~# '^\f\+_test\.go$'
    call go#test#Test(0, 1)
  elseif l:file =~# '^\f\+\.go$'
    call go#cmd#Build(0)
  endif
endfunction

" gometalinter configuration
let g:go_metalinter_command = ""
let g:go_metalinter_deadline = "5s"
let g:go_metalinter_enabled = [
    \ 'deadcode',
    \ 'errcheck',
    \ 'gas',
    \ 'goconst',
    \ 'gocyclo',
    \ 'golint',
    \ 'gosimple',
    \ 'ineffassign',
    \ 'vet',
    \ 'vetshadow'
    \]

" Python
""""""""

let python_highlight_all=1
let g:jedi#use_splits_not_buffers = 1
let g:jedi#completions_enabled = 0

if executable(glob('~/.config/nvim/py2/bin/python'))
    let g:python_host_prog = glob('~/.config/nvim/py2/bin/python')
endif

if executable(glob('~/.config/nvim/py3/bin/python'))
    let g:python3_host_prog = glob('~/.config/nvim/py3/bin/python')
endif


" mappings
au FileType go nmap <leader>r <Plug>(go-run)
au FileType go nmap <leader>b :<C-u>call <SID>build_go_files()<CR>
au FileType go nmap <leader>t <Plug>(go-test)
au FileType go nmap <leader>c <Plug>(go-coverage)

" git commit
""""""""""""
autocmd Filetype gitcommit setlocal cc=72


" FZF file finder plugin
""""""""""""""""""""""""
noremap <C-p> :FZF<CR>
let g:fzf_layout = { 'down': '~20%' }
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


" Ack.vim
"""""""""
if executable('ag')
  let g:ackprg = 'ag --vimgrep --smart-case'
endif
let g:ack_use_dispatch = 1


" Airline configuration
"""""""""""""""""""""""
let g:airline_powerline_fonts = 1
let g:airline_theme='one'


" Ale linter
""""""""""""
let g:ale_sign_error = '✗'
let g:ale_sign_warning = '⚠'
let g:ale_set_loclist = 1
let g:ale_open_list = 0
let g:ale_lint_on_text_changed = 'never'
let g:ale_linters = {
\   'go': ['gometalinter'],
\}
let g:ale_python_pylint_executable = ''

" YouCompleteMe
"""""""""""""""

let g:ycm_autoclose_preview_window_after_completion = 1
let g:ycm_filetype_specific_completion_to_disable = {'javascript': 1}
nnoremap <leader>g :YcmCompleter GoTo<CR>

" Deoplete
""""""""""
if has('nvim')
  let g:deoplete#enable_at_startup = 1

  let g:deoplete#sources#go#auto_goos = 1
  let g:deoplete#sources#go#gocode_binary = $GOPATH.'/bin/gocode'
  let g:deoplete#sources#go#sort_class = ['func', 'type', 'var', 'const', 'package']
endif

" Tagbar
""""""""

nmap <F8> :TagbarToggle<CR>
let g:tagbar_type_go = {
    \ 'ctagstype' : 'go',
    \ 'kinds'     : [
        \ 'p:package',
        \ 'i:imports:1',
        \ 'c:constants',
        \ 'v:variables',
        \ 't:types',
        \ 'n:interfaces',
        \ 'w:fields',
        \ 'e:embedded',
        \ 'm:methods',
        \ 'r:constructor',
        \ 'f:functions'
    \ ],
    \ 'sro' : '.',
    \ 'kind2scope' : {
        \ 't' : 'ctype',
        \ 'n' : 'ntype'
    \ },
    \ 'scope2kind' : {
        \ 'ctype' : 't',
        \ 'ntype' : 'n'
    \ },
    \ 'ctagsbin'  : 'gotags',
    \ 'ctagsargs' : '-sort -silent'
    \ }

" SuperTab
""""""""""
let g:SuperTabDefaultCompletionType = "<c-n>"

" vimrc auto-reload
"""""""""""""""""""
augroup myvimrc
    au!
    au BufWritePost .vimrc,_vimrc,vimrc,.gvimrc,_gvimrc,gvimrc so $MYVIMRC | if has('gui_running') | so $MYGVIMRC | endif
augroup END
