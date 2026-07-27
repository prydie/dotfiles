[[ -f ~/.zshenv.local ]] && source ~/.zshenv.local

# Keep unattended agent GitHub work independent of the desktop keyring. The
# token lives only in the per-login tmpfs and disappears on reboot/logout.
_nks_agent_github_token="${XDG_RUNTIME_DIR:-/run/user/$UID}/nks-agent-secrets/github.token"
if [[ -r "$_nks_agent_github_token" ]]; then
  export GH_TOKEN="$(<"$_nks_agent_github_token")"
fi
export GH_PROMPT_DISABLED=1
export GIT_TERMINAL_PROMPT=0
export SSH_ASKPASS_REQUIRE=never
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -o BatchMode=yes -o ConnectTimeout=20}"
unset _nks_agent_github_token

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
