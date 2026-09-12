#!/bin/bash
# Install agent skills using npx skills

set -uo pipefail

AGENTS=(--agent claude-code --agent codex --agent kiro-cli)

SKILLS_DIR="$HOME/.agents/skills"
failures=0

record_failure() {
  echo "Failed to $1" >&2
  failures=$((failures + 1))
}

install_skills() {
  local repo="$1"
  shift
  for skill in "$@"; do
    if ! skills add "$repo" --skill "$skill" -g "${AGENTS[@]}" -y < /dev/null; then
      record_failure "update skill: $skill"
    fi
  done
}

install_skills_claude_only() {
  local repo="$1"
  shift
  for skill in "$@"; do
    if ! skills add "$repo" --skill "$skill" -g --agent claude-code -y < /dev/null; then
      record_failure "update Claude Code skill: $skill"
    fi
  done
}

# Anthropic Skills
install_skills anthropics/skills \
  canvas-design doc-coauthoring frontend-design mcp-builder skill-creator

# AWS AgentCore Web Search. The skill drives the agentcore-websearch CLI, which
# ansible installs via uv; the gateway URL comes from AGENTCORE_GATEWAY_URL.
install_skills aws-samples/sample-agentcore-websearch-agent-skill agentcore-websearch

# hugohe3 PPT Master (paired with the ppt-master-aws wrapper skill).
# Deps live in a dedicated uv venv so they stay out of the system python3;
# the wrapper points ppt-master's scripts at it via PPT_MASTER_PYTHON.
# --upgrade on every apply keeps the pinned-range deps current.
install_skills hugohe3/ppt-master ppt-master
PPT_MASTER_VENV="${XDG_DATA_HOME:-$HOME/.local/share}/ppt-master/venv"
if [ ! -d "$PPT_MASTER_VENV" ]; then
  uv venv "$PPT_MASTER_VENV" --python 3.12 || record_failure "create ppt-master virtual environment"
fi
if [ -f "$SKILLS_DIR/ppt-master/requirements.txt" ]; then
  uv pip install --python "$PPT_MASTER_VENV/bin/python" --upgrade \
    -r "$SKILLS_DIR/ppt-master/requirements.txt" || record_failure "update ppt-master dependencies"
else
  record_failure "find ppt-master requirements"
fi

install_skills_claude_only anthropics/skills pdf

# Blader Humanizer
install_skills blader/humanizer humanizer

# Firecrawl anydoc
install_skills firecrawl/anydoc convert-documents-to-markdown

# Kepano Obsidian Skills
install_skills kepano/obsidian-skills \
  json-canvas obsidian-bases obsidian-markdown

# Matt Pocock Skills
install_skills mattpocock/skills grilling

# Obra Superpowers
install_skills obra/superpowers \
  brainstorming subagent-driven-development writing-plans

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

# OfficeCLI (iOfficeAI/OfficeCLI) — AI-friendly CLI for Office documents.
# Not distributed via `skills`; its own installer embeds the SKILL.md files and
# writes them into agent skill dirs. The `codex` target maps to ~/.agents/skills,
# which is the chezmoi-managed source of truth, so the .claude/.kiro symlinks
# stay valid. Installing here (rather than `chezmoi add`) keeps the skills in
# sync with the officecli binary on every apply.
if command -v officecli >/dev/null 2>&1; then
  officecli skills codex < /dev/null || record_failure "update OfficeCLI skill"
  for skill in pptx word excel; do
    officecli skills install "$skill" codex < /dev/null || record_failure "update OfficeCLI $skill skill"
  done
else
  record_failure "find officecli"
fi

if [ "$failures" -ne 0 ]; then
  echo "$failures skill installation step(s) failed" >&2
  exit 1
fi
