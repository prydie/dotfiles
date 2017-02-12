" Plugins (Plug)
""""""""""""""""

" Autoinstall Plug
if empty(glob('~/.local/share/nvim/plugged'))
  silent !curl -fLo ~/.local/share/nvim/site/autoload/plug.vim --create-dirs
    \ https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim
  autocmd VimEnter * PlugInstall | source $MYVIMRC
endif

call plug#begin('~/.local/share/nvim/plugged')

" Auto completion
Plug 'Shougo/deoplete.nvim', { 'do': ':UpdateRemotePlugins' }
Plug 'zchee/deoplete-jedi'
Plug 'zchee/deoplete-go'

" Misc.
Plug 'scrooloose/nerdtree'
Plug 'Xuyuanp/nerdtree-git-plugin'

Plug 'tpope/vim-fugitive'
Plug 'neomake/neomake'
Plug 'scrooloose/nerdcommenter'
Plug 'ervandew/supertab'

" text wrangling
Plug 'tpope/vim-surround'
Plug 'vimwiki/vimwiki'
Plug 'editorconfig/editorconfig-vim'

" UI
Plug 'vim-airline/vim-airline'
Plug 'airblade/vim-gitgutter'
Plug 'kshenoy/vim-signature'

" snippets
Plug 'SirVer/ultisnips'
Plug 'honza/vim-snippets'

" In-file searching ala 'ack'
Plug 'gabesoft/vim-ags'

" language specific
Plug 'fatih/vim-go', { 'do': ':GoInstallBinaries' }
Plug 'davidhalter/jedi-vim'

" Fuzzy file finder
Plug 'junegunn/fzf', { 'dir': '~/.fzf', 'do': './install --all' }
Plug 'junegunn/fzf.vim'

" Syntax highlighting
Plug 'stephpy/vim-yaml'
Plug 'Glench/Vim-Jinja2-Syntax'
Plug 'evanmiller/nginx-vim-syntax'
Plug 'pearofducks/ansible-vim'
Plug 'Matt-Deacalion/vim-systemd-syntax'

" Ctags tagbar
Plug 'majutsushi/tagbar'

" Markdown syntax augmentation
Plug 'tpope/vim-markdown'
Plug 'junegunn/goyo.vim'

" The all-important colorschemes
Plug 'iCyMind/NeoSolarized'
Plug 'morhetz/gruvbox'
Plug 'reedes/vim-colors-pencil'
Plug 'vim-airline/vim-airline-themes'
Plug 'mhartington/oceanic-next'

" Python
Plug 'fisadev/vim-isort', {'for': 'python'}

call plug#end()

" Colorscheme
"""""""""""""""""""""""
let $NVIM_TUI_ENABLE_CURSOR_SHAPE=1
if (has("termguicolors"))
 set termguicolors
endif

set background=dark
silent! colorscheme OceanicNext

" Basic configurations
""""""""""""""""""""""
set number              " Line numbers
set ignorecase!         " Ignore case in search
set hidden              " Hide instead of close bufffers to preserve history
set splitbelow          " Horizontal split below current.
set splitright          " Vertical split to right of current.
set vb                  " No error bells!
set colorcolumn=80      " Keep an eye on our line length.
set breakindent
set breakindentopt=sbr
set showbreak=↪>

" nvim Python hosts
let g:python_host_prog = expand('~') . '/.config/nvim/virtualenvs/neovim2/bin/python'
let g:python3_host_prog = expand('~') . '/.config/nvim/virtualenvs/neovim3/bin/python3.5'

" Where swap and backup files go
set backupdir=~/.config/nvim/backup_files//
set directory=~/.config/nvim/swap_files//
set undodir=~/.config/nvim/undo_files//

" Toggle highlight on \/
nnoremap <leader>/ :set hlsearch!<CR>

" Highlight VCS conflict markers
match ErrorMsg '^\(<\|=\|>\)\{7\}\([^=].\+\)\?$'

" Special characters for hilighting non-priting spaces/tabs/etc.
set list listchars=tab:»\ ,trail:·

hi Search ctermfg=0 ctermbg=11 guifg=Black guibg=Yellow
hi SpellBad ctermfg=15 ctermbg=9 guifg=White guibg=Red


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

" Tagbar/ctags
""""""""""""""
nmap <F8> :TagbarToggle<CR>

" NERDTree
""""""""""
noremap <c-n> :NERDTreeToggle<CR>

let NERDTreeIgnore = ['\.pyc$', '\.egg$', '\.o$', '\~$', '__pycache__$', '\.egg-info$', 'node_modules', 'htmlcov']

" Neomake settings (mainly linting)
"""""""""""""""""""""""""""""""""""
let g:neomake_verbose=0
let g:neomake_warning_sign = {
      \ 'text': '⚠',
      \ 'texthl': 'WarningMsg',
      \ }
let g:neomake_error_sign = {
      \ 'text': '✗',
      \ 'texthl': 'ErrorMsg',
      \ }

" pip install flake8
autocmd BufWritePost *.py Neomake flake8
" npm install -g eslint
autocmd BufWritePost *.js Neomake eslint

" :GoInstallBinaries
autocmd BufWritePost *.go Neomake go golint govet

" Airline configuration
"""""""""""""""""""""""

" Don't use powerline fonts
let g:airline_powerline_fonts = 0
let g:airline_symbols = {}

" Don't show separators
let g:airline_left_sep=''
let g:airline_right_sep=''

" Use theme for Airline
let g:airline_theme='oceanicnext'


" Tell Vim which characters to show for expanded TABs,
" trailing whitespace, and end-of-lines. VERY useful!
" (Sourced from http://nerditya.com/code/guide-to-neovim/)
if &listchars ==# 'eol:$'
  set listchars=tab:>\ ,trail:-,extends:>,precedes:<,nbsp:+
endif
set list                " Show problematic characters.

" Highlight all tabs and trailing whitespace characters.
highlight ExtraWhitespace ctermbg=red guibg=red
match ExtraWhitespace /\s\+\%#\@<!$/

" Editorconfig exceptions
"""""""""""""""""""""""""
let g:EditorConfig_exclude_patterns = ['fugitive://.*', 'scp://.*', '[Location List]']

" nerdcommenter
"""""""""""""""

" Align line-wise comment delimiters flush left instead of following code
" indentation
let g:NERDDefaultAlign = 'left'

" ultisnips
"""""""""""

" Trigger configuration.
let g:UltiSnipsExpandTrigger = "<tab>"
let g:UltiSnipsJumpForwardTrigger = "<c-j>"
let g:UltiSnipsJumpBackwardTrigger = "<c-k>"

" If you want :UltiSnipsEdit to split your window.
let g:UltiSnipsEditSplit = "vertical"
let g:UltiSnipsSnippetsDir = "~/.config/nvim/ultisnips"

" vim-ags
"""""""""
let g:ags_winheight = 15

" Deoplete autocomplete
"""""""""""""""""""""""
let g:deoplete#enable_at_startup=1
let g:deoplete#file#enable_buffer_path=1

" jedi-vim (excluding completion)
"""""""""""""""""""""""""""""""""
let g:jedi#completions_enabled = 0
autocmd BufWinEnter '__doc__' setlocal bufhidden=delete

" vim-wiki
"""""""""""""""""""""""""""""""""
let wiki = {}
let wiki.path = '~/Dropbox/Apps/vimwiki/'
let wiki.nested_syntaxes = {'python': 'python'}
let g:vimwiki_list = [wiki]
