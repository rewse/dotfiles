# Repository rules

Keep this file limited to repository-specific constraints that cannot be inferred from the source tree or standard chezmoi behavior.

## 1Password

- Store credentials in the `chezmoi` vault and keep credentials for different systems in separate items.
- Use `System - Consumer` only when both parts identify the credential. Use the complete product or service name for System and a stable username or service account for Consumer. Omit a part instead of filling it with a generic purpose, category, access key ID, client ID, UUID, MAC address, or other machine identifier.
- Use one-part names when appropriate: `Zabbix MCP Server` has no distinguishing Consumer, while `Tats Shibata` and `id_rsa` have no meaningful System.
- Use item IDs in committed Secret References so item renames do not break templates.

## Agent assets

| Asset | Source and distribution |
|---|---|
| Custom commands | Author in `dot_agents/commands/`. The existing directory symlinks expose them to Claude, Codex, and Kiro; do not add per-command symlinks. Include `description` frontmatter and `argument-hint` only when the command takes arguments. |
| Custom rules | Author in `.chezmoitemplates/rules/`, render through `dot_agents/rules/`, symlink into Claude and Kiro, and include in `dot_codex/AGENTS.md.tmpl`. |
| Custom skills | Author in `dot_agents/skills/<name>/SKILL.md` and add directory symlinks for Claude and Kiro. Codex discovers `$HOME/.agents/skills` directly, so do not add skills to `dot_codex/AGENTS.md.tmpl`. The `description` frontmatter must name every intended trigger context. |
| External commands | Configure selected files in `dot_agents/.chezmoiexternal.yaml`; they deploy under `commands/<source>/` and use namespaced command names. |
| External rules | Configure files in `dot_agents/.chezmoiexternal.yaml`, then symlink them into Claude and Kiro and include them in `dot_codex/AGENTS.md.tmpl`. |
| External skills | Add `install_skills <owner/repo> <skill>` to `run_install-skills.sh`. Put any idempotent post-install patch immediately after its install call. |

Prefer a skill to an always-loaded rule for task-specific reference material. When changing servers in `dot_config/mcporter/private_mcporter.json.tmpl`, update both the frontmatter description and server list in `dot_agents/skills/mcporter/SKILL.md.tmpl`.

## AWS

- Keep dependent AWS resource definitions outside this repository. The CloudFormation stacks live in account `070392599442`; recover a template with `aws cloudformation get-template --stack-name <stack> --region <region> | cat` and inspect parameters and outputs with `describe-stacks`.
- Stack `agentcore-websearch-caller` in `us-east-1` creates the `agentcore-websearch` IAM user and its gateway-only policy. Its access key is stored in 1Password as `AWS IAM - AgentCore Web Search` and rendered by `dot_aws/private_credentials.tmpl`; `dot_aws/private_config.tmpl` defines the profile.
- The Web Search gateway comes from `aws-samples/sample-agentcore-websearch-agent-skill`. Export its `GatewayUrl` output as `AGENTCORE_GATEWAY_URL` in `dot_zshenv.tmpl`.

## Commit types

- Use `docs:` for files under `.kiro/`.
- Do not use `docs:` for `dot_*` or `private_dot_*` files; choose `feat:`, `fix:`, `refactor:`, or `chore:` by intent.

## Managed files

- Do not manage `~/.claude/settings.json` or `~/.codex/config.toml` with chezmoi because corporate tools rewrite them. `dot_local/bin/executable_track-config-drift` records their history in `~/.local/share/config-drift.git`; add any new path to its `FILES` list.
- Treat live `~/.config/otty/config.toml` and `~/.kiro/agents/*.json` files as canonical even though chezmoi tracks them. Import tool changes with `chezmoi add` instead of correcting the source by hand.
- Keep `dot_aws/private_config.tmpl` comment-free and keep `[profile codex-DO-NOT-DELETE]` last because the Codex wrapper rewrites the file through an INI parser.
- If Claude's Bedrock `/model` list disappears, delete `~/.claude/.amzn/state/recommendation-snapshot.json` and start a session. `claude post-install` does not restore the list.

## Zed

Keep keys in `dot_config/zed/private_settings.json`, including nested keys, in the order used by Zed's bundled `default.json` for the installed version.
