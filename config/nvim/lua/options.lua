local o = vim.o

vim.g.mapleader = " "

o.laststatus = 3 -- global statusline
o.showmode = false

-- Use the system clipboard for all yank/paste.
o.clipboard = "unnamedplus"

-- Over SSH there is no usable local display server, and Nvim would otherwise pick
-- the *remote* host's wl-copy/xclip. Route yanks to OSC 52 so they reach the
-- terminal you are actually sitting at. Paste reads the unnamed register, since
-- terminal OSC 52 read-back is widely disabled.
if vim.env.SSH_TTY then
  local function paste()
    return vim.split(vim.fn.getreg "", "\n")
  end

  local copy_for
  if vim.env.TMUX then
    -- Inside tmux: hand the yank to tmux's buffer with -w, which makes tmux emit
    -- the OSC 52 to the outer terminal (see set-clipboard in tmux.conf). Works on
    -- any Nvim version, including the 0.9.x that ships on some target hosts.
    copy_for = function(_)
      return function(lines)
        vim.fn.system({ "tmux", "load-buffer", "-w", "-" }, table.concat(lines, "\n"))
      end
    end
  else
    -- No tmux: use Nvim's built-in OSC 52 provider (0.10+). Older Nvim outside
    -- tmux has no clean terminal write, so leave the default provider in place.
    local has_builtin, builtin = pcall(require, "vim.ui.clipboard.osc52")
    if has_builtin then
      copy_for = function(reg)
        return builtin.copy(reg)
      end
    end
  end

  if copy_for then
    vim.g.clipboard = {
      name = "OSC 52",
      copy = { ["+"] = copy_for "+", ["*"] = copy_for "*" },
      paste = { ["+"] = paste, ["*"] = paste },
    }
  end
end

-- Indenting
o.expandtab = true
o.shiftwidth = 2
-- o.smartindent = true
o.tabstop = 2
o.softtabstop = 2

vim.opt.fillchars = { eob = " " }
o.ignorecase = true
o.smartcase = true
o.mouse = "a"

o.number = true

o.signcolumn = "yes"
o.splitbelow = true
o.splitright = true
o.termguicolors = true
o.timeoutlen = 400
o.undofile = true
o.cursorline = true
o.colorcolumn = "80"
o.updatetime = 300
o.completeopt = "menu,menuone,noselect"
o.list = true
o.listchars = "tab:»\\ ,extends:›,precedes:‹,nbsp:·,trail:·"
o.incsearch = true
o.hlsearch = true

local mise_config = vim.fn.expand "~/.config/mise/config.toml"
if vim.fn.filereadable(mise_config) == 0 then
  mise_config = vim.fn.expand "~/.dotfiles/config/mise/config.toml"
end
if vim.fn.filereadable(mise_config) == 1 then
  vim.env.MISE_GLOBAL_CONFIG_FILE = mise_config
end

local vale_config = vim.fn.expand "~/.config/vale/vale.ini"
if vim.fn.filereadable(vale_config) == 0 then
  vale_config = vim.fn.expand "~/.dotfiles/config/vale/vale.ini"
end
if vim.fn.filereadable(vale_config) == 1 then
  vim.env.VALE_CONFIG_PATH = vale_config
end

-- add binaries installed by mason.nvim to path
local is_windows = vim.loop.os_uname().sysname == "Windows_NT"
local path_sep = is_windows and ";" or ":"
local path_parts = {
  vim.fn.expand "~/.local/share/mise/shims",
  vim.fn.expand "~/.local/bin",
  vim.fn.expand "~/go/bin",
  vim.fn.expand "~/.local/opt/go/bin",
  vim.env.PATH,
  vim.fn.stdpath "data" .. "/mason/bin",
}
vim.env.PATH = table.concat(path_parts, path_sep)

vim.api.nvim_set_hl(0, "IndentLine", { link = "Comment" })
