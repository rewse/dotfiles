#!/bin/bash
# Install agent skills using npx skills

set -uo pipefail

AGENTS=(--agent codex --agent kiro-cli)
# Claude Code is installed only on the business Mac; elsewhere a claude-code
# target would recreate ~/.claude, which .chezmoiignore leaves unmanaged there.
has_claude=false
if command -v claude >/dev/null 2>&1; then
  has_claude=true
  AGENTS+=(--agent claude-code)
fi

SKILLS_DIR="$HOME/.agents/skills"
failures=0
# ansible installs agent-desktop and officecli only on macOS, so their absence
# is a failure there and expected elsewhere.
is_darwin=false
[ "$(uname -s)" = Darwin ] && is_darwin=true

record_failure() {
  echo "Failed to $1" >&2
  failures=$((failures + 1))
}

# Third-party skills install from the commit that the default branch pointed
# at COOLDOWN_DAYS ago, matching npm's min-release-age and uv's exclude-newer,
# so a bad upstream push has time to be noticed and reverted before it reaches
# this machine.
COOLDOWN_DAYS=4
cooldown_epoch=$(($(date +%s) - COOLDOWN_DAYS * 86400))
# GNU date reads -d @EPOCH; BSD date reads -r EPOCH, which GNU takes as a file.
COOLDOWN_UNTIL="$(date -u -d "@$cooldown_epoch" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null ||
  date -u -r "$cooldown_epoch" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)"

# Prints the `skills add` source for a repository: OWNER/REPO#COMMIT past the
# cooldown, or OWNER/REPO for this account's own repositories, which track
# their default branch. Fails when GitHub returns no such commit.
#
# The commit comes from the repository activity, which records when GitHub
# moved the branch by a push or a merge, rather than from commit dates, which
# the publisher writes and can backdate. Only the newest 100 activities are
# read, so a branch that moved more often than that within the cooldown fails.
skill_source() {
  local repo="$1" branch commit
  case "$repo" in
    rewse/*)
      echo "$repo"
      return 0
      ;;
  esac
  [ -n "$COOLDOWN_UNTIL" ] || return 1
  branch="$(gh api "repos/$repo" --jq '.default_branch // empty' < /dev/null)" || return 1
  [ -n "$branch" ] || return 1
  # The timestamps share the cutoff's format, so they compare as strings. An
  # activity that left the branch at no commit, such as a deletion, is skipped.
  commit="$(gh api "repos/$repo/activity?ref=refs/heads/$branch&per_page=100" \
    --jq "[.[] | select(.activity_type != \"branch_deletion\"
      and .timestamp <= \"$COOLDOWN_UNTIL\"
      and (.after | tostring | test(\"^[0-9a-f]{40}$\") and (test(\"^0+$\") | not)))]
      | max_by(.timestamp) | .after // empty" \
    < /dev/null)" || return 1
  [[ "$commit" =~ ^[0-9a-f]{40}$ ]] || return 1
  echo "$repo#$commit"
}

# A source that does not resolve leaves the installed skills as they are rather
# than falling back to the unvetted default branch.
warn_kept() {
  echo "Warning: kept the installed $1 skills; no commit at least $COOLDOWN_DAYS days old resolved" >&2
}

install_skills() {
  local repo="$1" src
  shift
  if ! src="$(skill_source "$repo")"; then
    warn_kept "$repo"
    return 0
  fi
  for skill in "$@"; do
    if ! skills add "$src" --skill "$skill" -g "${AGENTS[@]}" -y < /dev/null; then
      record_failure "update skill: $skill"
    fi
  done
}

install_skills_claude_only() {
  local repo="$1" src
  shift
  "$has_claude" || return 0
  if ! src="$(skill_source "$repo")"; then
    warn_kept "$repo"
    return 0
  fi
  for skill in "$@"; do
    if ! skills add "$src" --skill "$skill" -g --agent claude-code -y < /dev/null; then
      record_failure "update Claude Code skill: $skill"
    fi
  done
}

# Prints the lines of a requirements file that are not a plain PyPI requirement:
# an option (another index, a requirements or constraints file, an editable
# install), a URL, or a VCS reference. Comments follow pip: # at the start of a
# line or after whitespace.
unsafe_requirements() {
  sed -E 's/(^|[[:space:]])#.*$//' "$1" | grep -nE '(^|[[:space:]])-|://|@|git\+'
}

# Anthropic Skills
install_skills anthropics/skills \
  canvas-design doc-coauthoring frontend-design mcp-builder

# AWS AgentCore Web Search. The skill drives the agentcore-websearch CLI, which
# ansible installs via uv; the gateway URL comes from AGENTCORE_GATEWAY_URL.
install_skills aws-samples/sample-agentcore-websearch-agent-skill agentcore-websearch

# hugohe3 PPT Master (paired with the ppt-master-aws wrapper skill).
# Deps live in a dedicated uv venv so they stay out of the system python3;
# the wrapper points ppt-master's scripts at it via PPT_MASTER_PYTHON.
# --upgrade on every apply keeps the pinned-range deps current. The upstream
# requirements may name only PyPI packages, which uv's exclude-newer holds to
# releases past the cooldown, and --no-build installs wheels only, so no
# package build script runs.
install_skills hugohe3/ppt-master ppt-master
PPT_MASTER_VENV="${XDG_DATA_HOME:-$HOME/.local/share}/ppt-master/venv"
PPT_MASTER_REQUIREMENTS="$SKILLS_DIR/ppt-master/requirements.txt"
if [ ! -d "$PPT_MASTER_VENV" ]; then
  uv venv "$PPT_MASTER_VENV" --python 3.12 || record_failure "create ppt-master virtual environment"
fi
if [ ! -f "$PPT_MASTER_REQUIREMENTS" ]; then
  record_failure "find ppt-master requirements"
elif unsafe_requirements "$PPT_MASTER_REQUIREMENTS" >&2; then
  record_failure "accept ppt-master requirements: the lines above are not plain PyPI requirements"
else
  uv pip install --python "$PPT_MASTER_VENV/bin/python" --upgrade --no-build \
    -r "$PPT_MASTER_REQUIREMENTS" || record_failure "update ppt-master dependencies"
fi

install_skills_claude_only anthropics/skills pdf

# Blader Humanizer
install_skills blader/humanizer humanizer

# Firecrawl anydoc
install_skills firecrawl/anydoc convert-documents-to-markdown

# HumanLayer Show Me
install_skills humanlayer/skills show-me

# Kepano Obsidian Skills
install_skills kepano/obsidian-skills \
  json-canvas obsidian-bases obsidian-markdown

# nanaism Yomiyasu
install_skills nanaism/yomiyasu yomiyasu

# Nico Bailon Visual Explainer
install_skills nicobailon/visual-explainer visual-explainer

# Obra Superpowers. Install every skill so new upstream skills arrive on the
# next apply; the skills cross-reference each other, so a partial set leaves
# dangling references. diagnosing-superpowers only debugs the plugin itself.
install_skills obra/superpowers '*'
skills remove -g -y diagnosing-superpowers < /dev/null ||
  record_failure "remove skill: diagnosing-superpowers"

# oharu121 Commands Skills Gems
install_skills oharu121/oharu-commands-skills-gems aws-architecture-diagram

# Oracle DB Skills
install_skills oracle/skills db

# Tavily AI. tavily-search covers extract, map and crawl in its references, and
# replaces the per-command skills that upstream removed; remove those so hosts
# that installed them earlier converge. The task skills send the agent to each
# other and tell it to install a missing one itself, so install them together.
# tavily-best-practices covers the SDKs, not the CLI, and is left out.
install_skills tavily-ai/skills \
  tavily-entity tavily-list tavily-monitor tavily-research tavily-search
skills remove -g -y tavily-cli tavily-crawl tavily-extract tavily-map < /dev/null ||
  record_failure "remove skills: tavily-cli tavily-crawl tavily-extract tavily-map"

# Upstash Context7
install_skills upstash/context7 find-docs

# Vercel Labs
install_skills vercel-labs/agent-browser agent-browser
install_skills vercel-labs/skills find-skills

# X Platform xurl
install_skills xdevplatform/xurl xurl

# Vercel Labs agent-desktop. Its skills are compiled into the binary, which
# ansible installs via npm, so writing the core guide out on every apply keeps
# the skill matched to the installed version. The guide loads the platform skill
# and its references from the binary on demand. A temporary file keeps the
# existing SKILL.md intact when the command fails or returns content without
# the frontmatter that agents need to discover the skill.
if command -v agent-desktop >/dev/null 2>&1; then
  agent_desktop_skill="$(mktemp /tmp/agent-desktop-skill.XXXXXX)"
  if agent-desktop skills get desktop < /dev/null |
    jq -er '.data.content | select(type == "string" and startswith("---\nname: agent-desktop\n"))' > "$agent_desktop_skill"; then
    if ! { chmod 0644 "$agent_desktop_skill" &&
      mkdir -p "$SKILLS_DIR/agent-desktop" &&
      command mv "$agent_desktop_skill" "$SKILLS_DIR/agent-desktop/SKILL.md"; }; then
      record_failure "write agent-desktop skill"
    fi
  else
    record_failure "update agent-desktop skill"
  fi
  command rm -f "$agent_desktop_skill"
elif "$is_darwin"; then
  record_failure "find agent-desktop"
fi

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
elif "$is_darwin"; then
  record_failure "find officecli"
fi

if [ "$failures" -ne 0 ]; then
  echo "$failures skill installation step(s) failed" >&2
  exit 1
fi
