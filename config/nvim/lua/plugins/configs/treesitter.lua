local opts = {
  ensure_installed = {
    "bash",
    "css",
    "dockerfile",
    "go",
    "gomod",
    "hcl",
    "html",
    "javascript",
    "json",
    "lua",
    "markdown",
    "markdown_inline",
    "python",
    "query",
    "terraform",
    "toml",
    "typescript",
    "vim",
    "vimdoc",
    "yaml",
  },

  highlight = {
    enable = true,
    use_languagetree = true,
  },
  indent = { enable = true },
}

-- nvim-treesitter main branch moved from `configs` module to `config`/`init` API.
local ok_new, ts = pcall(require, "nvim-treesitter")
if ok_new and type(ts.setup) == "function" then
  ts.setup(opts)
  return
end

local ok_old, ts_configs = pcall(require, "nvim-treesitter.configs")
if ok_old and type(ts_configs.setup) == "function" then
  ts_configs.setup(opts)
  return
end

vim.schedule(function()
  vim.notify("nvim-treesitter API not found; run :Lazy sync and restart Neovim", vim.log.levels.ERROR)
end)
