" Plugins (Plug)
""""""""""""""""

" Autoinstall Plug
if empty(glob('~/.config/nvim/autoload/plug.vim'))
  silent !curl -fLo ~/.config/nvim/autoload/plug.vim --create-dirs
        \ https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim
  autocmd VimEnter * PlugInstall
endif

call plug#begin('~/.config/nvim/plugged')

" General
Plug 'Shougo/deoplete.nvim'
Plug 'zchee/deoplete-jedi'
Plug 'davidhalter/jedi-vim'

Plug 'Xuyuanp/nerdtree-git-plugin' | Plug 'scrooloose/nerdtree', { 'on':  'NERDTreeToggle' }
Plug 'tpope/vim-fugitive'
Plug 'neomake/neomake'
Plug 'scrooloose/nerdcommenter'
Plug 'tpope/vim-surround'

" UI
Plug 'bling/vim-airline'
Plug 'airblade/vim-gitgutter'
Plug 'kshenoy/vim-signature'

Plug 'editorconfig/editorconfig-vim'
Plug 'ervandew/supertab'

" snippets
Plug 'SirVer/ultisnips'
Plug 'honza/vim-snippets'

" In-file searching ala 'ack'
Plug 'gabesoft/vim-ags'

" Fuzzy file finder
Plug 'junegunn/fzf', { 'dir': '~/.fzf', 'do': './install --all' }
Plug 'junegunn/fzf.vim'

" Syntax highlighting
Plug 'stephpy/vim-yaml'
Plug 'Glench/Vim-Jinja2-Syntax'

" Ctags tagbar
Plug 'majutsushi/tagbar'

" Allow better soft-wrapping of text in prose-based
" formats e.g. markdown.
Plug 'reedes/vim-pencil'

" Markdown syntax augmentation
Plug 'tpope/vim-markdown'
Plug 'junegunn/goyo.vim'

" The all-important colorschemes
Plug 'iCyMind/NeoSolarized'
Plug 'morhetz/gruvbox'
Plug 'reedes/vim-colors-pencil'
Plug 'vim-airline/vim-airline-themes'

" Python
Plug 'fisadev/vim-isort', {'for': 'python'}

call plug#end()

" Colorscheme
"""""""""""""""""""""""
set termguicolors
set background=dark
colorscheme NeoSolarized
let $NVIM_TUI_ENABLE_TRUE_COLOR=1
let $NVIM_TUI_ENABLE_CURSOR_SHAPE=1

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
" I use a unicode curly array with a <backslash><space>
set showbreak=↪>

" nvim Python hosts
let g:python_host_prog = '/home/andrew/.config/nvim/virtualenvs/neovim2/bin/python'
let g:python3_host_prog = '/home/andrew/.config/nvim/virtualenvs/neovim3/bin/python3.5'

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

" Airline configuration
"""""""""""""""""""""""

" Don't use powerline fonts
let g:airline_powerline_fonts = 0
let g:airline_symbols = {}

" Don't show separators
let g:airline_left_sep=''
let g:airline_right_sep=''

" Use theme for Airline
let g:airline_theme='papercolor'

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

" vim-pencil
""""""""""""
let g:pencil#wrapModeDefault = 'soft'   " default is 'hard'
augroup pencil
  autocmd!
  autocmd FileType markdown,mkd,liquid call pencil#init()
                            \ | setl spell spl=en_gb fdl=4 noru nonu nornu
                            \ | setl fdo+=search
  autocmd Filetype git,gitsendemail,*commit*,*COMMIT*
                            \   call pencil#init()
                            \ | setl spell spl=en_gb et sw=2 ts=2 tw=72 noai
  autocmd Filetype mail         call pencil#init({'wrap': 'hard', 'textwidth': 80})
                            \ | setl spell spl=en_gb et sw=2 ts=2 noai nonu nornu
  autocmd Filetype html,xml     call pencil#init({'wrap': 'soft'})
                            \ | setl spell spl=en_gb et sw=2 ts=2
augroup END

let g:airline_section_x = '%{PencilMode()}'

" Editorconfig exceptions
"""""""""""""""""""""""""
let g:EditorConfig_exclude_patterns = ['fugitive://.*', 'scp://.*']

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