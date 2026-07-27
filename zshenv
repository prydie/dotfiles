[[ -f ~/.zshenv.local ]] && source ~/.zshenv.local

if [[ -r /proc/$$/cgroup ]] &&
    [[ "$(< /proc/$$/cgroup)" == *"/agents.slice/"* ]]; then
  agent_test_shim_dir="$HOME/.dotfiles/libexec/agent-test-shims"
  if [[ "${NKS_AGENT_TEST_SHIMS_ACTIVE:-}" != 1 ]]; then
    export NKS_AGENT_TEST_ORIGINAL_PATH="$PATH"
    export NKS_AGENT_TEST_SHIMS_ACTIVE=1
  fi
  path=("$agent_test_shim_dir" ${path:#"$agent_test_shim_dir"})
  export PATH
  unset agent_test_shim_dir
fi

# alias docker="nerdctl"
