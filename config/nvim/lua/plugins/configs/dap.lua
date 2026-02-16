local dap = require "dap"
local dapui = require "dapui"

dapui.setup()

dap.listeners.after.event_initialized["dapui_config"] = function()
  dapui.open()
end
dap.listeners.before.event_terminated["dapui_config"] = function()
  dapui.close()
end
dap.listeners.before.event_exited["dapui_config"] = function()
  dapui.close()
end

local python_ok, dap_python = pcall(require, "dap-python")
if python_ok then
  dap_python.setup(vim.fn.exepath "python3")
end

local go_ok, dap_go = pcall(require, "dap-go")
if go_ok then
  dap_go.setup()
end
