vim.opt_local.wrap = true
vim.opt_local.linebreak = true
vim.opt_local.spell = true
vim.opt_local.textwidth = 80
vim.opt_local.colorcolumn = ""
vim.opt_local.conceallevel = 2

-- Keep automatic formatting focused on prose flow rather than code comments.
vim.opt_local.formatoptions:remove { "c", "r", "o" }
vim.opt_local.formatoptions:append { "t", "n" }
