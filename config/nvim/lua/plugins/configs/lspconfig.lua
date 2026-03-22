local root_markers = { "go.work", "go.mod", ".git" }

local function go_buf_dir(bufnr)
  local name = vim.api.nvim_buf_get_name(bufnr)
  if name == "" then
    return vim.uv.cwd()
  end

  return vim.fs.dirname(name)
end

local function go_root(bufnr)
  local start = go_buf_dir(bufnr)

  if vim.fs.root then
    return vim.fs.root(start, root_markers) or start
  end

  return start
end

local function go_term(cmd, cwd)
  Snacks.terminal(cmd, {
    cwd = cwd,
    auto_close = false,
    win = {
      position = "bottom",
      height = 0.25,
    },
  })
end

local function go_run(bufnr)
  go_term({ "go", "run", "." }, go_buf_dir(bufnr))
end

local function go_build(bufnr)
  go_term({ "go", "build", "./..." }, go_root(bufnr))
end

local function go_coverage(bufnr)
  go_term({ "go", "test", "-cover", "./..." }, go_root(bufnr))
end

local function setup_gopls(bufnr, client)
  if client.name ~= "gopls" then
    return
  end

  if vim.lsp.inlay_hint and client.server_capabilities.inlayHintProvider then
    vim.lsp.inlay_hint.enable(true, { bufnr = bufnr })
  end

  if client.server_capabilities.codeLensProvider then
    local group = vim.api.nvim_create_augroup("GoCodeLens" .. bufnr, { clear = true })

    vim.api.nvim_create_autocmd({ "BufEnter", "CursorHold", "InsertLeave" }, {
      buffer = bufnr,
      group = group,
      callback = function()
        pcall(vim.lsp.codelens.refresh)
      end,
    })

    vim.schedule(function()
      pcall(vim.lsp.codelens.refresh)
    end)
  end
end

vim.api.nvim_create_autocmd("LspAttach", {
  group = vim.api.nvim_create_augroup("UserLspConfig", {}),
  callback = function(ev)
    local opts = { buffer = ev.buf, silent = true }
    vim.bo[ev.buf].omnifunc = "v:lua.vim.lsp.omnifunc"
    local client = ev.data and vim.lsp.get_client_by_id(ev.data.client_id) or nil

    vim.keymap.set("n", "gD", vim.lsp.buf.declaration, vim.tbl_extend("force", opts, { desc = "Goto declaration" }))
    vim.keymap.set("n", "gd", vim.lsp.buf.definition, vim.tbl_extend("force", opts, { desc = "Goto definition" }))
    vim.keymap.set("n", "gi", vim.lsp.buf.implementation, vim.tbl_extend("force", opts, { desc = "Goto implementation" }))
    vim.keymap.set("n", "K", vim.lsp.buf.hover, vim.tbl_extend("force", opts, { desc = "Hover docs" }))
    vim.keymap.set("n", "<leader>rn", vim.lsp.buf.rename, vim.tbl_extend("force", opts, { desc = "Rename symbol" }))
    vim.keymap.set("n", "<leader>ca", vim.lsp.buf.code_action, vim.tbl_extend("force", opts, { desc = "Code action" }))
    vim.keymap.set("n", "<leader>fd", vim.lsp.buf.format, vim.tbl_extend("force", opts, { desc = "Format via LSP" }))

    if client then
      setup_gopls(ev.buf, client)
    end
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
  gopls = {
    settings = {
      gopls = {
        gofumpt = true,
        staticcheck = true,
        vulncheck = "Imports",
        usePlaceholders = true,
        completeFunctionCalls = true,
        codelenses = {
          generate = true,
          regenerate_cgo = true,
          run_govulncheck = true,
          tidy = true,
          upgrade_dependency = true,
          vendor = true,
        },
        hints = {
          assignVariableTypes = true,
          compositeLiteralFields = true,
          compositeLiteralTypes = true,
          constantValues = true,
          functionTypeParameters = true,
          parameterNames = true,
          rangeVariableTypes = true,
        },
        analyses = {
          nilness = true,
          shadow = true,
          unusedparams = true,
          unusedwrite = true,
          useany = true,
        },
      },
    },
  },
  helm_ls = {},
  html = {},
  jsonls = {},
  lua_ls = {},
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

return {
  go_build = go_build,
  go_coverage = go_coverage,
  go_run = go_run,
}
