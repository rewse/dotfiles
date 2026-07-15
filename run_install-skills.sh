#!/bin/bash
# Install agent skills using npx skills

set -uo pipefail

AGENTS="--agent claude-code --agent codex --agent kiro-cli"
AGENTS_NO_CLAUDE="--agent codex --agent kiro-cli"

SKILLS_DIR="$HOME/.agents/skills"
CLAUDE_SKILLS_DIR="$HOME/.claude/skills"

install_skills() {
  local repo="$1"
  shift
  for skill in "$@"; do
    if [ -d "$SKILLS_DIR/$skill" ]; then
      skills update "$skill" -g < /dev/null || true
    else
      skills add "$repo" --skill "$skill" -g $AGENTS -y || true
    fi
  done
}

install_skills_claude_only() {
  local repo="$1"
  shift
  for skill in "$@"; do
    if [ -d "$CLAUDE_SKILLS_DIR/$skill" ]; then
      skills update "$skill" -g < /dev/null || true
    else
      skills add "$repo" --skill "$skill" -g --agent claude-code -y || true
    fi
  done
}

# Anthropic Skills
install_skills anthropics/skills \
  canvas-design doc-coauthoring frontend-design mcp-builder skill-creator

# hugohe3 PPT Master (paired with the ppt-master-aws wrapper skill).
# Deps live in a dedicated uv venv so they stay out of the system python3;
# the wrapper points ppt-master's scripts at it via PPT_MASTER_PYTHON.
# --upgrade on every apply keeps the pinned-range deps current.
install_skills hugohe3/ppt-master ppt-master
PPT_MASTER_VENV="${XDG_DATA_HOME:-$HOME/.local/share}/ppt-master/venv"
[ -d "$PPT_MASTER_VENV" ] || uv venv "$PPT_MASTER_VENV" --python 3.12
uv pip install --python "$PPT_MASTER_VENV/bin/python" --upgrade \
  -r "$SKILLS_DIR/ppt-master/requirements.txt"

install_skills_claude_only anthropics/skills \
  docx pdf pptx xlsx

# Blader Humanizer
install_skills blader/humanizer humanizer

# Kepano Obsidian Skills
install_skills kepano/obsidian-skills \
  json-canvas obsidian-bases obsidian-markdown

# Manaflow cmux
install_skills manaflow-ai/cmux \
  cmux-browser cmux-markdown cmux

# Obra Superpowers
install_skills obra/superpowers \
  brainstorming writing-plans

# oharu121 Commands Skills Gems
install_skills oharu121/oharu-commands-skills-gems aws-architecture-diagram

# Oracle DB Skills
install_skills oracle/skills db

# Tavily AI
install_skills tavily-ai/skills \
  tavily-cli tavily-crawl tavily-extract tavily-map tavily-research tavily-search

# Upstash Context7
install_skills upstash/context7 find-docs

# Vercel Labs
install_skills vercel-labs/agent-browser agent-browser
install_skills vercel-labs/skills find-skills

# X Platform xurl
install_skills xdevplatform/xurl xurl
