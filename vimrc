call plug#begin('~/.vim/plugged')

" Sensible defaullts
Plug 'tpope/vim-sensible'

" Misc
Plug 'tpope/vim-dispatch'
Plug 'ervandew/supertab'
Plug 'vimwiki/vimwiki'
Plug 'Shougo/denite.nvim'

" Finding things
Plug 'junegunn/fzf', { 'dir': '~/.fzf', 'do': './install --all' }
Plug 'junegunn/fzf.vim'
Plug 'mileszs/ack.vim'

" Language support
Plug 'fatih/vim-go', { 'do': ':GoInstallBinaries' }
Plug 'sheerun/vim-polyglot'
Plug 'pangloss/vim-javascript'
Plug 'hashivim/vim-terraform'
Plug 'godlygeek/tabular'
Plug 'plasticboy/vim-markdown'
Plug 'towolf/vim-helm'
Plug 'chr4/nginx.vim'
Plug 'HerringtonDarkholme/yats.vim'
Plug 'mhartington/nvim-typescript', {'do': './install.sh'}

" Python import sorting
" NOTE: pip3 install --user isort
Plug 'stsewd/isort.nvim', { 'do': ':UpdateRemotePlugins' }
Plug 'hdima/python-syntax', { 'for': 'python' }
Plug 'davidhalter/jedi-vim', { 'for': 'python' }

" Omnicomplete
if has('nvim')
  "Plug 'Shougo/deoplete.nvim', { 'do': ':UpdateRemotePlugins' }
  "Plug 'zchee/deoplete-jedi', { 'for': 'python' }
  "Plug 'autozimu/LanguageClient-neovim', {
    "\ 'branch': 'next',
    "\ 'do': 'bash install.sh',
    "\ }
  Plug 'neoclide/coc.nvim', {'branch': 'release'}
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
Plug 'tommcdo/vim-fubitive'
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
set nowritebackup
set cmdheight=2                 " Give more space for displaying messages.
set noswapfile                  " No swap files
set completeopt+=noselect
set completeopt-=preview
set nocursorcolumn           " speed up syntax highlighting
set nocursorline
set updatetime=300
set pumheight=10             " Completion window max size
set diffopt+=vertical        " Always use vertical diffs
set shortmess+=c             " Don't pass messages to |ins-completion-menu|.

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
let g:go_def_mode='gopls'
let g:go_info_mode='gopls'

" Launch gopls when Go files are in use
let g:LanguageClient_serverCommands = {
       \ 'go': ['gopls']
       \ }

" run :GoBuild or :GoTestCompile based on the go file
function! s:build_go_files()
  let l:file = expand('%')
  if l:file =~# '^\f\+_test\.go$'
    call go#test#Test(0, 1)
  elseif l:file =~# '^\f\+\.go$'
    call go#cmd#Build(0)
  endif
endfunction

" Python
""""""""

let python_highlight_all=1
let g:jedi#use_splits_not_buffers = 1
let g:jedi#completions_enabled = 0
let g:jedi#goto_assignments_command = "gd"

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
\   'go': ['gopls'],
\   'js': ['eslint'],
\}
let g:ale_fixers = {'javascript': ['eslint']}
let g:ale_javascript_prettier_options = '--single-quote'
"let g:ale_go_gometalinter_options = '--tests --disable-all --aggregate --fast --sort=line --vendor --concurrency=16  --enable=gocyclo --enable=govet --enable=golint --enable=gotype --enable=deadcode'
let g:ale_go_golangci_lint_package=1
let g:ale_python_pylint_executable = ''

" Deoplete
""""""""""
"if has('nvim')
  "let g:deoplete#enable_at_startup = 1

  "let g:deoplete#sources#go#auto_goos = 1
  "let g:deoplete#sources#go#gocode_binary = $GOPATH.'/bin/gocode'
  "let g:deoplete#sources#go#sort_class = ['func', 'type', 'var', 'const', 'package']
"endif

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


" vimwiki
"""""""""
let g:vimwiki_list = [{'path': '~/vimwiki/', 'syntax': 'markdown', 'ext': '.md'}]


" vim-terraform
"""""""""""""""

let g:terraform_align=1

" vim-isort
"""""""""""
let g:vim_isort_python_version = 'python3'

" coc
"""""

" Always show the signcolumn, otherwise it would shift the text each time
" diagnostics appear/become resolved.
if has("patch-8.1.1564")
  " Recently vim can merge signcolumn and number column into one
  set signcolumn=number
else
  set signcolumn=yes
endif

" Use tab for trigger completion with characters ahead and navigate.
" NOTE: Use command ':verbose imap <tab>' to make sure tab is not mapped by
" other plugin before putting this into your config.
inoremap <silent><expr> <TAB>
      \ pumvisible() ? "\<C-n>" :
      \ <SID>check_back_space() ? "\<TAB>" :
      \ coc#refresh()
inoremap <expr><S-TAB> pumvisible() ? "\<C-p>" : "\<C-h>"

function! s:check_back_space() abort
  let col = col('.') - 1
  return !col || getline('.')[col - 1]  =~# '\s'
endfunction

" Use <c-space> to trigger completion.
if has('nvim')
  inoremap <silent><expr> <c-space> coc#refresh()
else
  inoremap <silent><expr> <c-@> coc#refresh()
endif

" Make <CR> auto-select the first completion item and notify coc.nvim to
" format on enter, <cr> could be remapped by other vim plugin
inoremap <silent><expr> <cr> pumvisible() ? coc#_select_confirm()
                              \: "\<C-g>u\<CR>\<c-r>=coc#on_enter()\<CR>"

" Use `[g` and `]g` to navigate diagnostics
" Use `:CocDiagnostics` to get all diagnostics of current buffer in location list.
nmap <silent> [g <Plug>(coc-diagnostic-prev)
nmap <silent> ]g <Plug>(coc-diagnostic-next)

" GoTo code navigation.
nmap <silent> gd <Plug>(coc-definition)
nmap <silent> gy <Plug>(coc-type-definition)
nmap <silent> gi <Plug>(coc-implementation)
nmap <silent> gr <Plug>(coc-references)

" Use K to show documentation in preview window.
nnoremap <silent> K :call <SID>show_documentation()<CR>

function! s:show_documentation()
  if (index(['vim','help'], &filetype) >= 0)
    execute 'h '.expand('<cword>')
  elseif (coc#rpc#ready())
    call CocActionAsync('doHover')
  else
    execute '!' . &keywordprg . " " . expand('<cword>')
  endif
endfunction

" Highlight the symbol and its references when holding the cursor.
autocmd CursorHold * silent call CocActionAsync('highlight')

" Symbol renaming.
nmap <leader>rn <Plug>(coc-rename)

" Formatting selected code.
xmap <leader>f  <Plug>(coc-format-selected)
nmap <leader>f  <Plug>(coc-format-selected)

augroup mygroup
  autocmd!
  " Setup formatexpr specified filetype(s).
  autocmd FileType typescript,json setl formatexpr=CocAction('formatSelected')
  " Update signature help on jump placeholder.
  autocmd User CocJumpPlaceholder call CocActionAsync('showSignatureHelp')
augroup end

" Applying codeAction to the selected region.
" Example: `<leader>aap` for current paragraph
xmap <leader>a  <Plug>(coc-codeaction-selected)
nmap <leader>a  <Plug>(coc-codeaction-selected)

" Remap keys for applying codeAction to the current buffer.
nmap <leader>ac  <Plug>(coc-codeaction)
" Apply AutoFix to problem on the current line.
nmap <leader>qf  <Plug>(coc-fix-current)

" Map function and class text objects
" NOTE: Requires 'textDocument.documentSymbol' support from the language server.
xmap if <Plug>(coc-funcobj-i)
omap if <Plug>(coc-funcobj-i)
xmap af <Plug>(coc-funcobj-a)
omap af <Plug>(coc-funcobj-a)
xmap ic <Plug>(coc-classobj-i)
omap ic <Plug>(coc-classobj-i)
xmap ac <Plug>(coc-classobj-a)
omap ac <Plug>(coc-classobj-a)

" Remap <C-f> and <C-b> for scroll float windows/popups.
" Note coc#float#scroll works on neovim >= 0.5.0 or vim >= 8.2.0750
nnoremap <expr><C-f> coc#float#has_scroll() ? coc#float#scroll(1) : "\<C-f>"
nnoremap <expr><C-b> coc#float#has_scroll() ? coc#float#scroll(0) : "\<C-b>"
inoremap <expr><C-f> coc#float#has_scroll() ? coc#float#scroll(1) : "\<Right>"
inoremap <expr><C-b> coc#float#has_scroll() ? coc#float#scroll(0) : "\<Left>"

" Use CTRL-S for selections ranges.
" Requires 'textDocument/selectionRange' support of language server.
nmap <silent> <C-s> <Plug>(coc-range-select)
xmap <silent> <C-s> <Plug>(coc-range-select)

" Add `:Format` command to format current buffer.
command! -nargs=0 Format :call CocAction('format')

" Add `:Fold` command to fold current buffer.
command! -nargs=? Fold :call     CocAction('fold', <f-args>)

" Add `:OR` command for organize imports of the current buffer.
command! -nargs=0 OR   :call     CocAction('runCommand', 'editor.action.organizeImport')

" Add (Neo)Vim's native statusline support.
" NOTE: Please see `:h coc-status` for integrations with external plugins that
" provide custom statusline: lightline.vim, vim-airline.
set statusline^=%{coc#status()}%{get(b:,'coc_current_function','')}

" Mappings for CoCList
" Show all diagnostics.
nnoremap <silent><nowait> <space>a  :<C-u>CocList diagnostics<cr>
" Manage extensions.
nnoremap <silent><nowait> <space>e  :<C-u>CocList extensions<cr>
" Show commands.
nnoremap <silent><nowait> <space>c  :<C-u>CocList commands<cr>
" Find symbol of current document.
nnoremap <silent><nowait> <space>o  :<C-u>CocList outline<cr>
" Search workspace symbols.
nnoremap <silent><nowait> <space>s  :<C-u>CocList -I symbols<cr>
" Do default action for next item.
nnoremap <silent><nowait> <space>j  :<C-u>CocNext<CR>
" Do default action for previous item.
nnoremap <silent><nowait> <space>k  :<C-u>CocPrev<CR>
" Resume latest coc list.
nnoremap <silent><nowait> <space>p  :<C-u>CocListResume<CR>
