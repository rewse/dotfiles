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
| Custom rules | Author in `.chezmoitemplates/rules/`, render through `dot_agents/rules/`, and symlink into Claude and Kiro. `dot_codex/AGENTS.md.tmpl` includes every file in that directory by glob, so do not add an include for a new rule. |
| Custom skills | Write user-invoked workflows as skills too, not as commands. Author in `dot_agents/skills/<name>/SKILL.md` and add directory symlinks for Claude and Kiro. Codex discovers `$HOME/.agents/skills` directly, so do not add skills to `dot_codex/AGENTS.md.tmpl`. The `description` frontmatter must cover every intended trigger context; name the categories of intent rather than listing example phrases, because descriptions load on every request. |
| External rules | Configure files in `dot_agents/.chezmoiexternal.yaml`, then symlink them into Claude and Kiro and include them in `dot_codex/AGENTS.md.tmpl`. |
| External skills | Add `install_skills <owner/repo> <skill>...` to `run_install-skills.sh`, or pass `'*'` when the repository's skills reference each other. Put any idempotent post-install patch immediately after its install call. |

Prefer a skill to an always-loaded rule for task-specific reference material. When changing servers in `dot_config/mcporter/private_mcporter.json.tmpl`, update both the frontmatter description and server list in `dot_agents/skills/mcporter/SKILL.md.tmpl`.

## AWS

- Keep dependent AWS resource definitions outside this repository. The CloudFormation stacks live in account `070392599442`; recover a template with `aws cloudformation get-template --stack-name <stack> --region <region> | cat` and inspect parameters and outputs with `describe-stacks`.
- Stack `agentcore-websearch-caller` in `us-east-1` creates the `agentcore-websearch` IAM user and its gateway-only policy. Its access key is stored in 1Password as `AWS IAM - AgentCore Web Search` and rendered by `dot_aws/private_credentials.tmpl`; `dot_aws/private_config.tmpl` defines the profile.
- The Web Search gateway comes from `aws-samples/sample-agentcore-websearch-agent-skill`. Export its `GatewayUrl` output as `AGENTCORE_GATEWAY_URL` in `dot_zshenv.tmpl`.

## Commit types

- Use `docs:` for `AGENTS.md` and files under `docs/`.
- Do not use `docs:` for `dot_*` or `private_dot_*` files; choose `feat:`, `fix:`, `refactor:`, or `chore:` by intent.

## Managed files

- Keep `AGENTS.md` and `docs` listed in `.chezmoiignore` so chezmoi does not deploy them to the home directory.
- Do not manage the whole of `~/.claude/settings.json` or `~/.codex/config.toml` with chezmoi because corporate tools rewrite them. `dot_claude/modify_settings.json.tmpl` only adds this repository's hooks and passes the file through unchanged once they are present; add Claude Code hooks there. `dot_local/bin/executable_track-config-drift` records the history of both files in `~/.local/share/config-drift.git`; add any new path to its `FILES` list.
- Treat the live `~/.config/otty/config.toml` as canonical even though chezmoi tracks it, and import tool changes with `chezmoi add` instead of correcting the source by hand. `~/.kiro/agents/default.json` renders from a template, so port Kiro's rewrites into `dot_kiro/agents/default.json.tmpl` instead.
- Otty also writes `~/.codex/hooks.json`, so `dot_codex/modify_hooks.json.tmpl` only adds this repository's hooks and passes the file through unchanged once they are present. Add Codex hooks there rather than managing the whole file.
- Keep `dot_aws/private_config.tmpl` comment-free and keep `[profile codex-DO-NOT-DELETE]` last because the Codex wrapper rewrites the file through an INI parser.
- If Claude's Bedrock `/model` list disappears, delete `~/.claude/.amzn/state/recommendation-snapshot.json` and start a session. `claude post-install` does not restore the list.

## Zed

Keep keys in `dot_config/zed/private_settings.json`, including nested keys, in the order used by Zed's bundled `default.json` for the installed version.
