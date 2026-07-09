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
