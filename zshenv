[[ -f ~/.zshenv.local ]] && source ~/.zshenv.local

if [[ -r /proc/$$/cgroup ]] &&
    [[ "$(< /proc/$$/cgroup)" == *"/agents.slice/"* ]]; then
  agent_test_shim_dir="$HOME/.dotfiles/libexec/agent-test-shims"
  if [[ -z "${NKS_AGENT_TEST_ORIGINAL_PATH:-}" ]]; then
    agent_test_original_path=(${path:#"$agent_test_shim_dir"})
    export NKS_AGENT_TEST_ORIGINAL_PATH="${(j.:.)agent_test_original_path}"
  fi
  export NKS_AGENT_TEST_SHIMS_ACTIVE=1
  path=("$agent_test_shim_dir" ${path:#"$agent_test_shim_dir"})
  export PATH
  unset agent_test_original_path agent_test_shim_dir
fi

# alias docker="nerdctl"
