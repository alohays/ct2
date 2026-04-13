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

info()    { echo -e "${GREEN}[ct2]${NC} $*"; }
warning() { echo -e "${YELLOW}[ct2 warn]${NC} $*"; }
error()   { echo -e "${RED}[ct2 error]${NC} $*" >&2; }

# ── Check dependencies ────────────────────────────────────────────────────────
if ! command -v git &>/dev/null; then
  error "git is required but not found. Install Xcode Command Line Tools: xcode-select --install"
  exit 1
fi

if ! command -v python3 &>/dev/null; then
  error "python3 is required but not found."
  exit 1
fi

# ── Clone or update CT2 repo ──────────────────────────────────────────────────
if [[ -d "$CT2_HOME/.git" ]]; then
  info "Updating existing CT2 installation at ${CT2_HOME}..."
  git -C "$CT2_HOME" pull --ff-only origin main || {
    warning "git pull failed; your local installation may be ahead of remote."
  }
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

# ── Add ~/.ct2/bin to PATH ─────────────────────────────────────────────────────
PATH_LINE='export PATH="${HOME}/.ct2/bin:${PATH}"'

# Detect shell config file
if [[ -n "${BASH_VERSION:-}" ]]; then
  SHELL_RC="${HOME}/.bash_profile"
elif [[ -n "${ZSH_VERSION:-}" ]]; then
  SHELL_RC="${HOME}/.zshrc"
else
  SHELL_RC="${HOME}/.zshrc"  # Default to zsh on modern macOS
fi

if ! grep -qF '.ct2/bin' "$SHELL_RC" 2>/dev/null; then
  echo "" >> "$SHELL_RC"
  echo "# CT2: Context Control Protocol" >> "$SHELL_RC"
  echo "$PATH_LINE" >> "$SHELL_RC"
  info "Added ~/.ct2/bin to PATH in ${SHELL_RC}"
else
  info "PATH already contains ~/.ct2/bin (skipping)"
fi

# Make bin scripts executable
chmod +x "${CT2_HOME}/bin/"*

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
echo -e "${GREEN}✓ CT2 installed successfully.${NC}"
echo ""
echo "Reload your shell or run:"
echo "  source ${SHELL_RC}"
echo ""
echo "Then, in a project directory:"
echo "  ct2-init          # Initialize .ct2/ in your project"
echo "  claude            # Open Claude Code"
echo "  /ct2:helm         # Enter planner role"
echo ""
echo "Full documentation: ${CT2_HOME}/spec/"
