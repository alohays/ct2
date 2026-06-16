#!/usr/bin/env bash
# CT2 Installer — Single-command install for macOS.
# Usage:
#   bash install.sh
#   bash install.sh --version v0.2.0
#   curl -fsSL https://raw.githubusercontent.com/alohays/ct2/main/install.sh | bash
#
# What this does:
#   1. Clones or updates ~/.ct2 from GitHub
#   2. Symlinks Claude Code skills into ~/.claude/skills/
#   3. Symlinks Codex skills into ~/.codex/skills/
#   4. Adds ~/.ct2/bin to PATH in ~/.zshrc (or ~/.bash_profile)

set -euo pipefail

CT2_REPO_URL="https://github.com/alohays/ct2"
CT2_HOME="${HOME}/.ct2"
CT2_INSTALL_VERSION="0.4.0"
SKILLS_SRC="${CT2_HOME}/claude-plugin/skills"
SKILLS_DST="${HOME}/.claude/skills"
CODEX_SKILLS_SRC="${CT2_HOME}/codex-plugin/skills"
CODEX_SKILLS_DST="${CODEX_HOME:-${HOME}/.codex}/skills"

# ── Terminal colors ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { printf '%b\n' "${GREEN}[ct2]${NC} $*"; }
warning() { printf '%b\n' "${YELLOW}[ct2 warn]${NC} $*"; }
error()   { printf '%b\n' "${RED}[ct2 error]${NC} $*" >&2; }

REQUESTED_REF=""
POSITIONAL=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      if [[ $# -lt 2 ]]; then
        error "--version requires a git ref such as v0.2.0 or main"
        exit 1
      fi
      REQUESTED_REF="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: bash install.sh [--version <tag-or-ref>]"
      echo "  --version v0.2.0  Install a pinned CT2 release tag"
      echo "  --version main    Install tip of main"
      exit 0
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done
set -- "${POSITIONAL[@]+"${POSITIONAL[@]}"}"

# ── Check dependencies ────────────────────────────────────────────────────────
if ! command -v git &>/dev/null; then
  if [[ "$(uname)" == "Darwin" ]]; then
    error "git is required but not found. Install Xcode Command Line Tools: xcode-select --install"
  else
    error "git is required but not found. Install with: sudo apt install git"
  fi
  exit 1
fi

if ! command -v python3 &>/dev/null; then
  if [[ "$(uname)" == "Darwin" ]]; then
    error "python3 is required but not found. Install Xcode CLT (xcode-select --install) or Homebrew (brew install python3)."
  else
    error "python3 is required but not found. Install with: sudo apt install python3"
  fi
  exit 1
fi

# Verify minimum Python version (3.9+)
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null; then
  error "Python 3.9+ required. Current: $(python3 --version 2>&1). Please upgrade."
  exit 1
fi

resolve_latest_ref() {
  python3 - "$CT2_REPO_URL" <<'PYEOF'
import re
import subprocess
import sys

repo = sys.argv[1]
proc = subprocess.run(
    ["git", "ls-remote", "--tags", "--refs", repo, "v*"],
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    check=False,
)
versions = []
for line in proc.stdout.splitlines():
    parts = line.split()
    if len(parts) != 2:
        continue
    ref = parts[1].rsplit("/", 1)[-1]
    match = re.fullmatch(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", ref)
    if match:
        versions.append((tuple(int(part) for part in match.groups()), ref))
if versions:
    print(sorted(versions)[-1][1])
PYEOF
}

if [[ -z "$REQUESTED_REF" ]]; then
  REQUESTED_REF="$(resolve_latest_ref || true)"
  if [[ -z "$REQUESTED_REF" ]]; then
    REQUESTED_REF="main"
    warning "No release tag found; installing main."
  else
    info "Installing latest stable CT2 release (${REQUESTED_REF}). Use --version main for tip-of-tree."
  fi
else
  info "Installing CT2 ref ${REQUESTED_REF}."
fi

# ── Clone or update CT2 repo ──────────────────────────────────────────────────
if [[ -d "$CT2_HOME/.git" ]]; then
  info "Updating existing CT2 installation at ${CT2_HOME}..."
  # Heartbeat files live inside each project's .ct2/.meta/, not inside $CT2_HOME,
  # so we cannot scan for them reliably from here. Nudge the user to stop any
  # active sessions first — mid-update drift can change SKILL.md semantics while
  # a live forge/lens loop still references the old version in its context.
  warning "If any CT2 sessions (forge, lens-cc, lens-cx) are running,"
  warning "stop them before this update to avoid mid-session semantic drift."
  git -C "$CT2_HOME" fetch --tags origin || {
    warning "git fetch failed; your local installation may stay on its current ref."
  }
  if [[ "$REQUESTED_REF" == "main" ]]; then
    git -C "$CT2_HOME" checkout main >/dev/null 2>&1 || true
    git -C "$CT2_HOME" pull --ff-only origin main || {
      warning "git pull failed; your local installation may be ahead of remote."
    }
  else
    git -C "$CT2_HOME" checkout "$REQUESTED_REF" || {
      error "Unable to checkout ${REQUESTED_REF}. Check that the tag or branch exists."
      exit 1
    }
  fi
elif [[ -d "$CT2_HOME" ]]; then
  error "${CT2_HOME} exists but is not a CT2 git repository."
  error "Back up and remove it, then re-run install.sh:"
  error "  mv ${CT2_HOME} ${CT2_HOME}.bak && bash install.sh"
  exit 1
else
  info "Installing CT2 to ${CT2_HOME}..."
  git clone "$CT2_REPO_URL" "$CT2_HOME"
  if [[ "$REQUESTED_REF" != "main" ]]; then
    git -C "$CT2_HOME" checkout "$REQUESTED_REF" || {
      error "Unable to checkout ${REQUESTED_REF}. Check that the tag or branch exists."
      exit 1
    }
  fi
fi

# ── Symlink skills into ~/.claude/skills/ ─────────────────────────────────────
info "Symlinking Claude Code skills..."
mkdir -p "$SKILLS_DST"

for skill_dir in "${SKILLS_SRC}"/*/; do
  [[ -d "$skill_dir" ]] || continue
  skill_name=$(basename "$skill_dir")
  target="${SKILLS_DST}/${skill_name}"

  # Remove stale symlink or old directory
  if [[ -L "$target" ]]; then
    rm "$target"
  elif [[ -d "$target" ]]; then
    warning "${target} exists as a real directory; skipping (remove manually to update)"
    continue
  fi

  ln -sfn "$skill_dir" "$target"
  info "  linked: ${target} → ${skill_dir}"
done

# ── Symlink skills into ~/.codex/skills/ ─────────────────────────────────────
if [[ -d "$CODEX_SKILLS_SRC" ]]; then
  info "Symlinking Codex skills..."
  mkdir -p "$CODEX_SKILLS_DST"

  for skill_dir in "${CODEX_SKILLS_SRC}"/*/; do
    [[ -d "$skill_dir" ]] || continue
    skill_name=$(basename "$skill_dir")
    target="${CODEX_SKILLS_DST}/${skill_name}"

    if [[ -L "$target" ]]; then
      rm "$target"
    elif [[ -d "$target" ]]; then
      warning "${target} exists as a real directory; skipping (remove manually to update)"
      continue
    fi

    ln -sfn "$skill_dir" "$target"
    info "  linked: ${target} → ${skill_dir}"
  done
fi

# ── Create env.sh for PATH (rustup-style idempotent sourcing) ─────────────────
ENV_FILE="${CT2_HOME}/env.sh"
cat > "$ENV_FILE" << 'ENVEOF'
# CT2: Protocol for Multi-Agent Code Operations — PATH setup (sourced from shell RC)
case ":${PATH}:" in
  *:"${HOME}/.ct2/bin":*) ;;
  *) export PATH="${HOME}/.ct2/bin:${PATH}" ;;
esac
ENVEOF
info "Created ${ENV_FILE}"

# ── Add source line to shell RC ───────────────────────────────────────────────
# Detect user's login shell (not the script's interpreter)
LOGIN_SHELL="$(basename -- "${SHELL:-bash}")"
case "$LOGIN_SHELL" in
  zsh)
    SHELL_RC="${ZDOTDIR:-${HOME}}/.zshrc"
    ;;
  bash)
    if [[ "$(uname)" == "Darwin" ]]; then
      SHELL_RC="${HOME}/.bash_profile"
    else
      SHELL_RC="${HOME}/.bashrc"
    fi
    ;;
  *)
    SHELL_RC="${ENV:-${HOME}/.profile}"
    ;;
esac

SOURCE_LINE='. "${HOME}/.ct2/env.sh"'
if ! grep -qF '.ct2/env.sh' "$SHELL_RC" 2>/dev/null; then
  echo "" >> "$SHELL_RC"
  echo "# CT2: Protocol for Multi-Agent Code Operations" >> "$SHELL_RC"
  echo "$SOURCE_LINE" >> "$SHELL_RC"
  info "Added CT2 PATH source to ${SHELL_RC}"
else
  info "CT2 PATH already configured in ${SHELL_RC} (skipping)"
fi

# Make bin scripts and hook scripts executable
chmod +x "${CT2_HOME}/bin/"*
chmod +x "${CT2_HOME}/claude-plugin/hooks/"*.sh 2>/dev/null || true

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
printf '%b\n' "${GREEN}✓ CT2 installed successfully.${NC}"
echo ""
echo "Reload your shell or run:"
echo "  source ${SHELL_RC}"

# Warn if Claude Code is not detected
if ! command -v claude &>/dev/null; then
  echo ""
  warning "Claude Code CLI not found. CT2 requires Claude Code to function."
  warning "Install from: https://claude.ai/claude-code"
fi
if ! command -v codex &>/dev/null; then
  echo ""
  warning "Codex CLI not found. Install Codex to use CT2 Codex roles:"
  warning "  https://github.com/openai/codex"
else
  echo ""
  info "Codex support can be checked in any initialized project with:"
  info "  ct2-codex-doctor"
  info "Codex app-server control is available through:"
  info "  ct2-codex-app-driver"
  if [[ -f "${CT2_HOME}/.agents/plugins/marketplace.json" ]]; then
    info "Codex plugin marketplace metadata is available at:"
    info "  ${CT2_HOME}/.agents/plugins/marketplace.json"
  fi
fi
echo ""
echo "Then, in a project directory:"
echo "  ct2-init          # Initialize .ct2/ in your project"
echo "  claude            # Open Claude Code"
echo "  /ct2:helm         # Enter planner role"
echo "  ct2-codex-doctor  # Check Codex CLI feature support"
echo "  ct2-codex-app-driver ct2-status \"Inspect CT2 state\" --sandbox read-only"
echo "  ct2-lens-cx       # Start the Codex reviewer adapter"
echo ""
echo "Full documentation: ${CT2_HOME}/spec/"
