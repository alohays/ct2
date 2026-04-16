#!/usr/bin/env bash
# CT2 Installer — Single-command install for macOS.
# Usage:
#   bash install.sh
#   curl -fsSL https://raw.githubusercontent.com/alohays/ct2/main/install.sh | bash
#
# What this does:
#   1. Clones or updates ~/.ct2 from GitHub
#   2. Symlinks Claude Code skills into ~/.claude/skills/
#   3. Adds ~/.ct2/bin to PATH in ~/.zshrc (or ~/.bash_profile)

set -euo pipefail

CT2_REPO_URL="https://github.com/alohays/ct2"
CT2_HOME="${HOME}/.ct2"
SKILLS_SRC="${CT2_HOME}/claude-plugin/skills"
SKILLS_DST="${HOME}/.claude/skills"

# ── Terminal colors ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { printf '%b\n' "${GREEN}[ct2]${NC} $*"; }
warning() { printf '%b\n' "${YELLOW}[ct2 warn]${NC} $*"; }
error()   { printf '%b\n' "${RED}[ct2 error]${NC} $*" >&2; }

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

# ── Clone or update CT2 repo ──────────────────────────────────────────────────
if [[ -d "$CT2_HOME/.git" ]]; then
  info "Updating existing CT2 installation at ${CT2_HOME}..."
  git -C "$CT2_HOME" pull --ff-only origin main || {
    warning "git pull failed; your local installation may be ahead of remote."
  }
elif [[ -d "$CT2_HOME" ]]; then
  error "${CT2_HOME} exists but is not a CT2 git repository."
  error "Back up and remove it, then re-run install.sh:"
  error "  mv ${CT2_HOME} ${CT2_HOME}.bak && bash install.sh"
  exit 1
else
  info "Installing CT2 to ${CT2_HOME}..."
  git clone "$CT2_REPO_URL" "$CT2_HOME"
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

# ── Create env.sh for PATH (rustup-style idempotent sourcing) ─────────────────
ENV_FILE="${CT2_HOME}/env.sh"
cat > "$ENV_FILE" << 'ENVEOF'
# CT2: Context Control Protocol — PATH setup (sourced from shell RC)
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
  echo "# CT2: Context Control Protocol" >> "$SHELL_RC"
  echo "$SOURCE_LINE" >> "$SHELL_RC"
  info "Added CT2 PATH source to ${SHELL_RC}"
else
  info "CT2 PATH already configured in ${SHELL_RC} (skipping)"
fi

# Make bin scripts and hook scripts executable
chmod +x "${CT2_HOME}/bin/"*
chmod +x "${CT2_HOME}/claude-plugin/hooks/"*.sh 2>/dev/null || true

# ── Copy launchd plist template (macOS only) ─────────────────────────────────
if [[ "$(uname)" == "Darwin" ]]; then
  LAUNCH_AGENTS="${HOME}/Library/LaunchAgents"
  PLIST_SRC="${CT2_HOME}/launchd/com.ct2.lens-cx.plist.template"
  if [[ -f "$PLIST_SRC" ]]; then
    info "launchd plist template available at:"
    info "  ${PLIST_SRC}"
    info "  Copy and customize it, then load with: launchctl load ~/Library/LaunchAgents/com.ct2.lens-cx.plist"
  fi
fi

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
echo ""
echo "Then, in a project directory:"
echo "  ct2-init          # Initialize .ct2/ in your project"
echo "  claude            # Open Claude Code"
echo "  /ct2:helm         # Enter planner role"
echo ""
echo "Full documentation: ${CT2_HOME}/spec/"
