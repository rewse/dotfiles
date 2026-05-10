{{- /* Source: https://github.com/aws/agent-toolkit-for-aws/blob/main/rules/aws-agent-rules.md */ -}}
# AWS Guidance

- Before starting a task, check whether a relevant AWS skill is available. You MUST run `mcporter call aws-mcp.aws___search_documentation search_phrase="..."` to discover available skills, then `mcporter call aws-mcp.aws___retrieve_skill skill_name="<skill-name>"` to load the skill and prefer its guidance over general knowledge. Do NOT use `npx skills find/search` for AWS skill discovery.
- When creating infrastructure, prefer infrastructure-as-code (AWS CDK or CloudFormation) over direct CLI commands.
