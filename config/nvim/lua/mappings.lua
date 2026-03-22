local map = vim.keymap.set

-- general mappings
map({ "n", "i", "v" }, "<C-s>", "<cmd>w<CR>")
map("i", "jk", "<ESC>")
map("n", "<C-c>", "<cmd>%y+<CR>") -- copy whole filecontent
map("n", "<leader><Space>", "<cmd>nohlsearch<CR>", { desc = "Clear search highlight" })
map("n", "<C-h>", "<C-w>h", { desc = "Move to left split" })
map("n", "<C-j>", "<C-w>j", { desc = "Move to lower split" })
map("n", "<C-k>", "<C-w>k", { desc = "Move to upper split" })
map("n", "<C-l>", "<C-w>l", { desc = "Move to right split" })

-- nvimtree
map("n", "<C-n>", "<cmd>Neotree toggle<CR>", { desc = "Toggle file tree" })

local fzf_ok, fzf = pcall(require, "fzf-lua")
if fzf_ok then
  map("n", "<leader>p", fzf.files, { desc = "FZF Files" })
  map("n", "<leader><leader>", fzf.resume, { desc = "FZF Resume" })
  map("n", "<leader>fw", fzf.live_grep, { desc = "FZF Grep" })
  map("n", "<leader>fb", fzf.buffers, { desc = "FZF Buffers" })
  map("n", "<leader>gs", fzf.git_status, { desc = "Git Status" })
  map("n", "<leader>s", fzf.spell_suggest, { desc = "Spelling Suggestions" })
else
  map("n", "<leader>p", "<cmd>echo 'fzf-lua unavailable'<CR>", { desc = "FZF Files" })
end

-- diagnostics
map("n", "<Leader>ds", vim.diagnostic.open_float, { desc = "Show diagnostic" })
map("n", "<leader>q", function()
  vim.diagnostic.setloclist { open = true }
end, { desc = "Open buffer diagnostics" })
map("n", "<leader>Q", function()
  require("trouble").toggle {
    mode = "diagnostics",
    filter = { buf = 0 },
  }
end, { desc = "Workspace diagnostics (Trouble)" })

-- bufferline, cycle buffers
map("n", "<Tab>", "<cmd>BufferLineCycleNext<CR>")
map("n", "<S-Tab>", "<cmd>BufferLineCyclePrev<CR>")
map("n", "<C-q>", "<cmd>bd<CR>")

-- comment.nvim
map("n", "<leader>/", "gcc", { remap = true, desc = "Comment line" })
map("v", "<leader>/", "gc", { remap = true, desc = "Comment selection" })

-- format
map("n", "<leader>fm", function()
  local ok, conform = pcall(require, "conform")
  if ok then
    conform.format()
  else
    vim.notify("conform.nvim unavailable", vim.log.levels.WARN)
  end
end, { desc = "[F]ormat File" })

-- infra / kube / esp32 commands
map("n", "<leader>tf", "<cmd>TofuFmt<CR>", { desc = "Tofu format recursive" })
map("n", "<leader>ka", "<cmd>KubeApply<CR>", { desc = "kubectl apply current file" })
map("n", "<leader>kd", "<cmd>KubeDryRun<CR>", { desc = "kubectl dry-run current file" })
map("n", "<leader>ke", "<cmd>KubeExplain<CR>", { desc = "kubectl explain word" })
map("n", "<leader>eb", "<cmd>IdfBuild<CR>", { desc = "idf.py build" })
map("n", "<leader>ef", "<cmd>IdfFlash<CR>", { desc = "idf.py flash" })
map("n", "<leader>em", "<cmd>IdfMonitor<CR>", { desc = "idf.py monitor" })
map("n", "<leader>dt", "<cmd>DjangoTestFile<CR>", { desc = "pytest current file" })

-- debug
map("n", "<leader>db", function()
  local ok, dap = pcall(require, "dap")
  if ok then
    dap.toggle_breakpoint()
  end
end, { desc = "Toggle breakpoint" })
map("n", "<leader>dc", function()
  local ok, dap = pcall(require, "dap")
  if ok then
    dap.continue()
  end
end, { desc = "Debug continue" })
map("n", "<leader>di", function()
  local ok, dap = pcall(require, "dap")
  if ok then
    dap.step_into()
  end
end, { desc = "Debug step into" })
map("n", "<leader>dn", function()
  local ok, dap = pcall(require, "dap")
  if ok then
    dap.step_over()
  end
end, { desc = "Debug step over" })
map("n", "<leader>do", function()
  local ok, dap = pcall(require, "dap")
  if ok then
    dap.step_out()
  end
end, { desc = "Debug step out" })
map("n", "<leader>du", function()
  local ok, dapui = pcall(require, "dapui")
  if ok then
    dapui.toggle()
  end
end, { desc = "Toggle debug UI" })

-- symbols outline (Tagbar replacement)
map("n", "<leader>a", "<cmd>AerialToggle!<CR>", { desc = "Toggle symbols outline" })

-- Go convenience mappings (vim-go style analogs)
vim.api.nvim_create_autocmd("FileType", {
  pattern = "go",
  callback = function(ev)
    local opts = { buffer = ev.buf, silent = true }
    map("n", "<leader>rr", "<cmd>GoRun<CR>", vim.tbl_extend("force", opts, { desc = "Go Run package" }))
    map("n", "<leader>rb", "<cmd>GoBuild<CR>", vim.tbl_extend("force", opts, { desc = "Go Build workspace" }))
    map("n", "<leader>rc", "<cmd>GoCoverage<CR>", vim.tbl_extend("force", opts, { desc = "Go Coverage" }))
    map("n", "<leader>td", function()
      require("neotest").run.run { strategy = "dap" }
    end, vim.tbl_extend("force", opts, { desc = "Debug nearest test" }))
    map("n", "<leader>tD", function()
      require("neotest").run.run { vim.fn.expand "%", strategy = "dap" }
    end, vim.tbl_extend("force", opts, { desc = "Debug file" }))
  end,
})
