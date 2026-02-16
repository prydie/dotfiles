local M = {}

local compose_filenames = {
  "docker-compose.yml",
  "docker-compose.yaml",
  "compose.yml",
  "compose.yaml",
}

local service_priority = {
  "web",
  "app",
  "django",
  "server",
  "api",
}
local container_tool_cache = {}
local service_probe_cache = {}
local infra_service_patterns = {
  "rabbit",
  "redis",
  "postgres",
  "mysql",
  "mariadb",
  "mongo",
  "kafka",
  "zookeeper",
  "minio",
  "vault",
  "prometheus",
  "grafana",
  "nginx",
  "traefik",
}

local function file_exists(path)
  return vim.fn.filereadable(path) == 1
end

local function shell_join(parts)
  local out = {}
  for _, part in ipairs(parts) do
    table.insert(out, vim.fn.shellescape(part))
  end
  return table.concat(out, " ")
end

local function run_systemlist(cmd)
  local out = vim.fn.systemlist(cmd)
  if vim.v.shell_error ~= 0 then
    return {}
  end
  return out
end

local function run_system(cmd)
  vim.fn.system(cmd)
  return vim.v.shell_error == 0
end

local function project_wants_uv(root_dir)
  if vim.env.VIM_DJANGO_USE_UV == "1" then
    return true
  end
  if vim.env.VIM_DJANGO_USE_UV == "0" then
    return false
  end
  return file_exists(root_dir .. "/uv.lock")
end

local function inspect_compose_tools(runtime)
  local key = runtime.compose_file .. "::" .. runtime.service
  if container_tool_cache[key] ~= nil then
    return container_tool_cache[key]
  end

  local lines = run_systemlist({
    "docker",
    "compose",
    "-f",
    runtime.compose_file,
    "exec",
    "-T",
    runtime.service,
    "sh",
    "-lc",
    "for c in uv python python3 pytest; do command -v \"$c\" >/dev/null 2>&1 && echo \"$c\"; done",
  })

  local found = {}
  for _, tool in ipairs(lines) do
    found[tool] = true
  end
  container_tool_cache[key] = found
  return found
end

local function pytest_launcher(runtime)
  local root = runtime and runtime.compose_dir or vim.fn.getcwd()
  local prefer_uv = project_wants_uv(root)

  local tools = {}
  if runtime then
    tools = inspect_compose_tools(runtime)
  else
    tools.uv = vim.fn.executable("uv") == 1
    tools.python = vim.fn.executable("python") == 1
    tools.python3 = vim.fn.executable("python3") == 1
    tools.pytest = vim.fn.executable("pytest") == 1
  end

  if (prefer_uv or vim.env.VIM_DJANGO_FORCE_UV == "1") and tools.uv then
    return { "uv", "run", "pytest" }
  end

  if tools.python then
    return { "python", "-m", "pytest" }
  end

  if tools.python3 then
    return { "python3", "-m", "pytest" }
  end

  if tools.pytest then
    return { "pytest" }
  end

  -- Final fallback; command will fail loudly with a clear shell error.
  if runtime then
    return { "python3", "-m", "pytest" }
  end

  if project_wants_uv(root) then
    return { "uv", "run", "pytest" }
  end

  return { "python3", "-m", "pytest" }
end

local function priority_rank(service)
  for idx, candidate in ipairs(service_priority) do
    if candidate == service then
      return idx
    end
  end
  return #service_priority + 1
end

local function is_infra_service(service)
  local lower = service:lower()
  for _, pattern in ipairs(infra_service_patterns) do
    if lower:find(pattern, 1, true) then
      return true
    end
  end
  return false
end

local function probe_service(compose_file, service)
  local key = compose_file .. "::" .. service
  if service_probe_cache[key] ~= nil then
    return service_probe_cache[key]
  end

  local lines = run_systemlist({
    "docker",
    "compose",
    "-f",
    compose_file,
    "exec",
    "-T",
    service,
    "sh",
    "-lc",
    "tools=0; command -v uv >/dev/null 2>&1 && tools=1; command -v python >/dev/null 2>&1 && tools=1; command -v python3 >/dev/null 2>&1 && tools=1; command -v pytest >/dev/null 2>&1 && tools=1; django=0; [ -f manage.py ] && django=1; [ -f /app/manage.py ] && django=1; [ -f ./src/manage.py ] && django=1; echo \"$tools $django\"",
  })

  local tools = 0
  local django = 0
  if #lines > 0 then
    local t, d = lines[1]:match("^(%d+)%s+(%d+)$")
    tools = tonumber(t or "0") or 0
    django = tonumber(d or "0") or 0
  end

  local score = tools * 2 + django * 4
  local result = { score = score, has_tools = tools == 1, has_django = django == 1 }
  service_probe_cache[key] = result
  return result
end

local function service_score(service, running_set)
  local lower = service:lower()
  local score = 0

  if is_infra_service(service) then
    score = score - 100
  end

  local exact_rank = priority_rank(service)
  if exact_rank <= #service_priority then
    score = score + (200 - exact_rank)
  else
    for idx, token in ipairs(service_priority) do
      if lower:find(token, 1, true) then
        score = score + (120 - idx)
        break
      end
    end
  end

  if running_set[service] then
    score = score + 25
  end

  return score
end

local function choose_service(compose_file, configured_services, running_services)
  if #configured_services == 0 and #running_services == 0 then
    return nil
  end

  local running_set = {}
  for _, svc in ipairs(running_services) do
    running_set[svc] = true
  end

  local preferred = vim.env.VIM_DJANGO_SERVICE
  if preferred and preferred ~= "" then
    if running_set[preferred] then
      return preferred
    end
    for _, svc in ipairs(configured_services) do
      if svc == preferred then
        return preferred
      end
    end
  end

  local candidates = configured_services
  if #candidates == 0 then
    candidates = running_services
  end

  local best = nil
  local best_score = -math.huge
  for _, svc in ipairs(candidates) do
    local score = service_score(svc, running_set)
    -- secondary tie-breaker: prefer services we can probe successfully
    local probe = probe_service(compose_file, svc)
    if probe.has_tools then
      score = score + 5
    end
    if probe.has_django then
      score = score + 10
    end

    if not best then
      best = svc
      best_score = score
    else
      local same_score_better_priority = score == best_score and priority_rank(svc) < priority_rank(best)
      if score > best_score or same_score_better_priority then
        best = svc
        best_score = score
      end
    end
  end

  return best
end

local function find_compose_file(start_dir)
  local user_file = vim.env.VIM_DJANGO_COMPOSE_FILE
  if user_file and user_file ~= "" and file_exists(user_file) then
    return vim.fn.fnamemodify(user_file, ":p")
  end

  local current = start_dir
  while current and current ~= "" do
    for _, name in ipairs(compose_filenames) do
      local candidate = current .. "/" .. name
      if file_exists(candidate) then
        return vim.fn.fnamemodify(candidate, ":p")
      end
    end
    local parent = vim.fn.fnamemodify(current, ":h")
    if parent == current then
      break
    end
    current = parent
  end

  return nil
end

function M.detect_django_runtime()
  if vim.fn.executable("docker") == 0 then
    return nil
  end

  local cwd = vim.fn.getcwd()
  local compose_file = find_compose_file(cwd)
  if not compose_file then
    return nil
  end

  local compose_dir = vim.fn.fnamemodify(compose_file, ":h")
  local running_services = run_systemlist({
    "docker",
    "compose",
    "-f",
    compose_file,
    "ps",
    "--services",
    "--status",
    "running",
  })

  local configured_services = run_systemlist({
    "docker",
    "compose",
    "-f",
    compose_file,
    "config",
    "--services",
  })

  local service = choose_service(compose_file, configured_services, running_services)
  if not service then
    return nil
  end

  return {
    compose_file = compose_file,
    compose_dir = compose_dir,
    service = service,
  }
end

function M.relative_to_compose_root(path, compose_dir)
  local abs = vim.fn.fnamemodify(path, ":p")
  local root = vim.fn.fnamemodify(compose_dir, ":p")
  if root:sub(-1) == "/" then
    root = root:sub(1, -2)
  end

  local prefix = root .. "/"
  if abs:sub(1, #prefix) ~= prefix then
    return nil
  end

  local rel = abs:sub(#prefix + 1)
  if rel == "" then
    return nil
  end
  return rel
end

function M.build_compose_exec_prefix(runtime)
  local running = run_systemlist({
    "docker",
    "compose",
    "-f",
    runtime.compose_file,
    "ps",
    "--services",
    "--status",
    "running",
    runtime.service,
  })

  if #running > 0 then
    return shell_join({
      "docker",
      "compose",
      "-f",
      runtime.compose_file,
      "exec",
      "-T",
      runtime.service,
    })
  end

  return shell_join({
    "docker",
    "compose",
    "-f",
    runtime.compose_file,
    "run",
    "--rm",
    "--no-deps",
    runtime.service,
  })
end

function M.build_pytest_executable(runtime)
  local launcher = pytest_launcher(runtime)
  if runtime then
    return M.build_compose_exec_prefix(runtime) .. " " .. shell_join(launcher)
  end
  return shell_join(launcher)
end

local function has_vim_test()
  return vim.fn.exists(":TestNearest") == 2
end

local function configure_vim_test_for_runtime(runtime)
  vim.g["test#python#pytest#executable"] = M.build_pytest_executable(runtime)
end

local function run_vim_test(cmd, runtime)
  if not has_vim_test() then
    return false
  end

  local old_cwd = vim.fn.getcwd()
  if runtime then
    vim.cmd("lcd " .. vim.fn.fnameescape(runtime.compose_dir))
  end
  configure_vim_test_for_runtime(runtime)
  vim.cmd(cmd)
  if runtime then
    vim.cmd("lcd " .. vim.fn.fnameescape(old_cwd))
  end
  return true
end

function M.run_django_manage(args)
  local manage_args = args or {}
  local runtime = M.detect_django_runtime()

  if runtime then
    local cmd = M.build_compose_exec_prefix(runtime) .. " " .. shell_join(vim.list_extend({ "python", "manage.py" }, manage_args))
    vim.cmd("!" .. cmd)
    return
  end

  vim.cmd("!" .. shell_join(vim.list_extend({ "python", "manage.py" }, manage_args)))
end

function M.run_django_test_current_file()
  local runtime = M.detect_django_runtime()
  if run_vim_test("TestFile", runtime) then
    return
  end

  local current_file = vim.fn.expand("%:p")
  if runtime then
    local rel = M.relative_to_compose_root(current_file, runtime.compose_dir) or current_file
    local cmd = M.build_compose_exec_prefix(runtime) .. " " .. shell_join(vim.list_extend(pytest_launcher(runtime), { "-q", rel }))
    vim.cmd("!" .. cmd)
    return
  end
  vim.cmd("!" .. shell_join(vim.list_extend(pytest_launcher(nil), { "-q", vim.fn.expand "%" })))
end

function M.run_django_test_nearest()
  local runtime = M.detect_django_runtime()
  if run_vim_test("TestNearest", runtime) then
    return
  end
  M.run_django_test_current_file()
end

function M.run_django_test_last()
  local runtime = M.detect_django_runtime()
  if run_vim_test("TestLast", runtime) then
    return
  end
  vim.notify("TestLast unavailable without vim-test", vim.log.levels.WARN)
end

function M.django_runtime_info()
  local runtime = M.detect_django_runtime()
  if not runtime then
    vim.notify("Django runtime: host (no docker compose stack detected)", vim.log.levels.INFO)
    return
  end

  vim.notify(
    "Django runtime: compose file=" .. runtime.compose_file .. ", service=" .. runtime.service,
    vim.log.levels.INFO
  )
end

return M
