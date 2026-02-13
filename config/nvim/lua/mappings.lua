local map = vim.keymap.set

-- general mappings
map("n", "<C-s>", "<cmd> w <CR>")
map("i", "jk", "<ESC>")
map("n", "<C-c>", "<cmd> %y+ <CR>") -- copy whole filecontent

-- nvimtree
map("n", "<C-n>", "<cmd> Neotree <CR>")
-- map("n", "<C-h>", "<cmd> NvimTreeFocus <CR>")

-- telescope
-- map("n", "<leader>ff", "<cmd> Telescope find_files <CR>", { desc = "[F]ind [F]iles"})
-- map("n", "<leader>fo", "<cmd> Telescope oldfiles <CR>")
-- map("n", "<leader>fw", "<cmd> Telescope live_grep <CR>", { desc = "[F]ind [W]"})
-- map("n", "<leader>gt", "<cmd> Telescope git_status <CR>")
map("n", "<leader>p", require("fzf-lua").files, { desc = "FZF Files" })

map("n", "<leader><leader>", require("fzf-lua").resume, { desc = "FZF Resume" })

map("n", "<leader>fw", require("fzf-lua").live_grep, { desc = "FZF Grep" })

map("n", "<leader>fb", require("fzf-lua").buffers, { desc = "FZF Buffers" })

map("n", "<leader>gs", require("fzf-lua").git_status, { desc = "Git Status" })

map("n", "<leader>s", require("fzf-lua").spell_suggest, { desc = "Spelling Suggestions" })


-- diagnostics
map("n", "<Leader>ds", vim.diagnostic.open_float, { desc = "Show diagnostic" })
vim.keymap.set('n', '<leader>q', vim.diagnostic.setloclist, { desc = 'Open diagnostic [Q]uickfix list' })

-- bufferline, cycle buffers
map("n", "<Tab>", "<cmd> BufferLineCycleNext <CR>")
map("n", "<S-Tab>", "<cmd> BufferLineCyclePrev <CR>")
map("n", "<C-q>", "<cmd> bd <CR>")

-- comment.nvim
map("n", "<leader>/", "gcc", { remap = true }, { desc = "Comment code"})
map("v", "<leader>/", "gc", { remap = true })

-- format
map("n", "<leader>fm", function()
  require("conform").format()
end, {desc = "[F]ormat File"})
