vim.api.nvim_create_autocmd("LspAttach", {
  group = vim.api.nvim_create_augroup("UserLspConfig", {}),
  callback = function(ev)
    local opts = { buffer = ev.buf, silent = true }
    vim.bo[ev.buf].omnifunc = "v:lua.vim.lsp.omnifunc"

    vim.keymap.set("n", "gD", vim.lsp.buf.declaration, vim.tbl_extend("force", opts, { desc = "Goto declaration" }))
    vim.keymap.set("n", "gd", vim.lsp.buf.definition, vim.tbl_extend("force", opts, { desc = "Goto definition" }))
    vim.keymap.set("n", "gi", vim.lsp.buf.implementation, vim.tbl_extend("force", opts, { desc = "Goto implementation" }))
    vim.keymap.set("n", "K", vim.lsp.buf.hover, vim.tbl_extend("force", opts, { desc = "Hover docs" }))
    vim.keymap.set("n", "<leader>rn", vim.lsp.buf.rename, vim.tbl_extend("force", opts, { desc = "Rename symbol" }))
    vim.keymap.set("n", "<leader>ca", vim.lsp.buf.code_action, vim.tbl_extend("force", opts, { desc = "Code action" }))
    vim.keymap.set("n", "<leader>fd", vim.lsp.buf.format, vim.tbl_extend("force", opts, { desc = "Format via LSP" }))
  end,
})

local capabilities = vim.lsp.protocol.make_client_capabilities()
local blink_ok, blink = pcall(require, "blink.cmp")
if blink_ok and blink.get_lsp_capabilities then
  capabilities = blink.get_lsp_capabilities(capabilities)
end

local server_configs = {
  bashls = {},
  cssls = {},
  dockerls = {},
  gopls = {},
  helm_ls = {},
  html = {},
  jsonls = {},
  lua_ls = {},
  pyright = {},
  terraformls = {},
  yamlls = {
    settings = {
      yaml = {
        keyOrdering = false,
        schemaStore = { enable = true },
        format = { enable = true },
        validate = true,
      },
    },
  },
  ansiblels = {
    settings = {
      ansible = {
        validation = { enabled = true },
      },
    },
  },
  clangd = {
    capabilities = vim.tbl_deep_extend("force", capabilities, { offsetEncoding = { "utf-16" } }),
    cmd = {
      "clangd",
      "--background-index",
      "--clang-tidy",
      "--header-insertion=iwyu",
      "--completion-style=detailed",
      "--function-arg-placeholders",
      "--fallback-style=llvm",
      "--query-driver=/home/andrew/.espressif/tools/xtensa-esp32-elf/**/bin/*gcc",
    },
  },
}

if vim.lsp.config and vim.lsp.enable then
  vim.lsp.config("*", { capabilities = capabilities })
  for name, conf in pairs(server_configs) do
    vim.lsp.config(name, conf)
  end
  local servers = vim.tbl_keys(server_configs)
  table.sort(servers)
  vim.lsp.enable(servers)
else
  local lspconfig = require "lspconfig"
  for name, conf in pairs(server_configs) do
    if name ~= "clangd" then
      conf.capabilities = capabilities
    end
    lspconfig[name].setup(conf)
  end
end
