local project_env = require "project_env"
local lspconfig = require "plugins.configs.lspconfig"

local function project_root()
  return vim.fs.root(vim.api.nvim_buf_get_name(0), { "go.work", "go.mod", ".git" }) or vim.fn.getcwd()
end

local function project_golangci_lint()
  local local_bin = project_root() .. "/bin/golangci-lint"
  if vim.fn.executable(local_bin) == 1 then
    return local_bin
  end
  return "golangci-lint"
end

local function golangci_command()
  local root = project_root()
  local local_bin = root .. "/bin/golangci-lint"

  if vim.fn.filereadable(root .. "/.custom-gcl.yml") == 1 then
    if vim.fn.executable(local_bin) == 1 then
      return { local_bin, "run", "./..." }
    end

    vim.notify(
      "Project uses a custom golangci-lint plugin build. Run `make golangci-lint` in the repo first.",
      vim.log.levels.WARN,
      { title = "GoLint" }
    )
    return nil
  end

  return { project_golangci_lint(), "run", "./..." }
end

local function shell_join(cmd)
  local escaped = {}
  for _, arg in ipairs(cmd) do
    table.insert(escaped, vim.fn.shellescape(arg))
  end
  return table.concat(escaped, " ")
end

local function run_terminal(cmd, opts)
  opts = opts or {}
  local executable = cmd[1]
  if vim.fn.executable(executable) ~= 1 then
    vim.notify(executable .. " is not available on PATH", vim.log.levels.ERROR, { title = opts.title or "Command" })
    return
  end

  Snacks.terminal(cmd, {
    cwd = opts.cwd or project_root(),
    auto_close = false,
    win = {
      position = "bottom",
      height = 0.3,
    },
  })
end

-- mason, write correct names only
vim.api.nvim_create_user_command("MasonInstallAll", function()
  vim.cmd "MasonInstall bash-language-server css-lsp dockerfile-language-server html-lsp json-lsp lua-language-server pyright yaml-language-server ansible-language-server terraform-ls helm-ls gopls goimports gofumpt golangci-lint clangd stylua prettier black isort shfmt shellcheck tflint hadolint delve debugpy"
end, {})

vim.api.nvim_create_user_command("GoRun", function()
  lspconfig.go_run(vim.api.nvim_get_current_buf())
end, {})

vim.api.nvim_create_user_command("GoBuild", function()
  lspconfig.go_build(vim.api.nvim_get_current_buf())
end, {})

vim.api.nvim_create_user_command("GoCoverage", function()
  lspconfig.go_coverage(vim.api.nvim_get_current_buf())
end, {})

vim.api.nvim_create_user_command("GoVet", function()
  run_terminal({ "go", "vet", "./..." }, { title = "GoVet" })
end, {})

vim.api.nvim_create_user_command("GoLint", function()
  local cwd = project_root()
  local cmd = golangci_command()
  if not cmd then
    return
  end

  run_terminal(cmd, { cwd = cwd, title = "GoLint" })
end, {})

vim.api.nvim_create_user_command("GoVulnCheck", function()
  run_terminal({ "govulncheck", "./..." }, { title = "GoVulnCheck" })
end, {})

vim.api.nvim_create_user_command("GoVerify", function()
  local cwd = project_root()
  local lint_cmd = golangci_command()
  if not lint_cmd then
    return
  end

  local commands = {
    { "go", "test", "./..." },
    { "go", "vet", "./..." },
    { "govulncheck", "./..." },
    lint_cmd,
  }

  for _, cmd in ipairs(commands) do
    local executable = cmd[1]
    if vim.fn.executable(executable) ~= 1 then
      vim.notify(executable .. " is not available on PATH", vim.log.levels.ERROR, { title = "GoVerify" })
      return
    end
  end

  local parts = {}
  for _, cmd in ipairs(commands) do
    table.insert(parts, shell_join(cmd))
  end

  run_terminal({ "bash", "-lc", table.concat(parts, " && ") }, { cwd = cwd, title = "GoVerify" })
end, {})

vim.api.nvim_create_user_command("TofuFmt", function()
  vim.cmd "!tofu fmt -recursive"
end, {})

vim.api.nvim_create_user_command("KubeApply", function()
  vim.cmd "!kubectl apply -f %"
end, {})

vim.api.nvim_create_user_command("KubeDryRun", function()
  vim.cmd "!kubectl apply --dry-run=server -f %"
end, {})

vim.api.nvim_create_user_command("KubeExplain", function(opts)
  local target = opts.args ~= "" and opts.args or vim.fn.expand "<cword>"
  vim.cmd("!kubectl explain " .. target)
end, { nargs = "?" })

vim.api.nvim_create_user_command("DjangoTestFile", function()
  project_env.run_django_test_current_file()
end, {})

vim.api.nvim_create_user_command("DjangoTestNearest", function()
  project_env.run_django_test_nearest()
end, {})

vim.api.nvim_create_user_command("DjangoTestLast", function()
  project_env.run_django_test_last()
end, {})

vim.api.nvim_create_user_command("DjangoTestSuite", function()
  local runtime = project_env.detect_django_runtime()
  if runtime then
    local old_cwd = vim.fn.getcwd()
    vim.g["test#python#pytest#executable"] = project_env.build_pytest_executable(runtime)
    vim.cmd("lcd " .. vim.fn.fnameescape(runtime.compose_dir))
    vim.cmd "TestSuite"
    vim.cmd("lcd " .. vim.fn.fnameescape(old_cwd))
    return
  end
  vim.g["test#python#pytest#executable"] = project_env.build_pytest_executable(nil)
  vim.cmd "TestSuite"
end, {})

vim.api.nvim_create_user_command("DjangoManage", function(opts)
  project_env.run_django_manage(opts.fargs)
end, { nargs = "+" })

vim.api.nvim_create_user_command("DjangoRuntimeInfo", function()
  project_env.django_runtime_info()
end, {})

vim.api.nvim_create_user_command("IdfBuild", function()
  vim.cmd "!idf.py build"
end, {})

vim.api.nvim_create_user_command("IdfFlash", function()
  vim.cmd "!idf.py flash"
end, {})

vim.api.nvim_create_user_command("IdfMonitor", function()
  vim.cmd "!idf.py monitor"
end, {})
