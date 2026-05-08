#!/bin/bash
# Install agent skills using npx skills

set -euo pipefail

AGENTS="--agent claude-code --agent codex --agent kiro-cli"
AGENTS_NO_CLAUDE="--agent codex --agent kiro-cli"

SKILLS_DIR="$HOME/.agents/skills"
CLAUDE_SKILLS_DIR="$HOME/.claude/skills"

install_skills() {
  local repo="$1"
  shift
  for skill in "$@"; do
    if [ -d "$SKILLS_DIR/$skill" ]; then
      skills update "$skill" -g
    else
      skills add "$repo" --skill "$skill" -g $AGENTS -y
    fi
  done
}

install_skills_claude_only() {
  local repo="$1"
  shift
  for skill in "$@"; do
    if [ -d "$CLAUDE_SKILLS_DIR/$skill" ]; then
      skills update "$skill" -g
    else
      skills add "$repo" --skill "$skill" -g --agent claude-code -y
    fi
  done
}

install_skills_no_claude() {
  local repo="$1"
  shift
  for skill in "$@"; do
    if [ -d "$SKILLS_DIR/$skill" ]; then
      skills update "$skill" -g
    else
      skills add "$repo" --skill "$skill" -g $AGENTS_NO_CLAUDE -y
    fi
  done
}

# Anthropic Skills
install_skills anthropics/skills \
  canvas-design doc-coauthoring frontend-design mcp-builder skill-creator webapp-testing
install_skills_claude_only anthropics/skills \
  docx pdf pptx xlsx

# Blader Humanizer
install_skills blader/humanizer humanizer

# Corey Haines Marketing Skills
install_skills coreyhaines31/marketingskills \
  copy-editing copywriting marketing-ideas marketing-psychology programmatic-seo social-content

# Kepano Obsidian Skills
install_skills kepano/obsidian-skills \
  json-canvas obsidian-bases obsidian-markdown

# Microsoft HVE Core
install_skills microsoft/hve-core powerpoint

# Microsoft Playwright CLI
install_skills microsoft/playwright-cli playwright-cli

# MiniMax Skills
install_skills MiniMax-AI/skills \
  minimax-docx minimax-pdf minimax-xlsx

# Obra Superpowers
install_skills obra/superpowers brainstorming

# oharu121 Commands Skills Gems
install_skills oharu121/oharu-commands-skills-gems aws-architecture-diagram

# OpenAI Skills
install_skills_no_claude openai/skills pdf

# Oracle DB Skills
install_skills oracle/skills db

# sirkirby unifi-mcp Skills
install_skills sirkirby/unifi-mcp \
  firewall-auditor firewall-manager network-health-check unifi-network

# Upstash Context7
install_skills upstash/context7 find-docs

# Vercel Labs
install_skills vercel-labs/agent-browser agent-browser
install_skills vercel-labs/agent-skills web-design-guidelines
install_skills vercel-labs/skills find-skills

# X Platform xurl
install_skills xdevplatform/xurl xurl
