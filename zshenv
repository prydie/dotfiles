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

# Base PATH + tool managers. Set here in .zshenv (sourced by ALL zsh invocations,
# including non-interactive ssh commands, cron, and agent runs) rather than only
# .zshrc, so mise-managed tools and ~/.local/bin binaries (claude, mise itself)
# resolve outside interactive sessions too. Putting mise's shims dir on PATH is
# mise's recommended non-interactive integration; .zshrc layers the richer
# `mise activate` hook (per-directory env, chpwd) on top for interactive use.
typeset -U path
path=(
  "$HOME/.local/bin"
  "$HOME/bin"
  "$HOME/go/bin"
  "$HOME/.local/share/mise/shims"
  "/opt/nvim-linux-x86_64/bin"
  $path
)
export PATH
export GOPATH="$HOME/go"
export MISE_GLOBAL_CONFIG_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/mise/config.toml"
if [[ ! -f "$MISE_GLOBAL_CONFIG_FILE" && -f "$HOME/.dotfiles/config/mise/config.toml" ]]; then
  export MISE_GLOBAL_CONFIG_FILE="$HOME/.dotfiles/config/mise/config.toml"
fi

if [[ -r /proc/$$/cgroup ]] &&
    [[ "$(< /proc/$$/cgroup)" == *"/agents.slice/"* ]]; then
  agent_test_shim_dir="$HOME/.dotfiles/libexec/agent-test-shims"
  export GIT_CONFIG_COUNT=2
  export GIT_CONFIG_KEY_0=commit.gpgSign
  export GIT_CONFIG_VALUE_0=false
  export GIT_CONFIG_KEY_1=gpg.program
  export GIT_CONFIG_VALUE_1="$HOME/.dotfiles/libexec/agent-gpg-noninteractive"
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
