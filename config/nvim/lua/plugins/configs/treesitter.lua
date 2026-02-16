local ok, ts_configs = pcall(require, "nvim-treesitter.configs")
if not ok then
  vim.schedule(function()
    vim.notify("nvim-treesitter not available; run :Lazy sync", vim.log.levels.WARN)
  end)
  return
end

ts_configs.setup {
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
