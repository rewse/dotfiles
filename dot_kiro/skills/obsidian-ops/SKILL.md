---
name: obsidian-ops
description: Guide for operating Obsidian vault using the `obsidian` command. Use when the user wants to read, search, create, or manage notes in Obsidian. Trigger when the user mentions "obsidian", "vault", "note", "handover", "ノート", "メモ", "引継書", "Obsidian に書いて", "ノートを作って", "メモを残して", "ノートを探して", "ノートを読んで", or any task involving reading, writing, searching, or organizing notes. Even if the user doesn't explicitly say "Obsidian", trigger this skill when they ask to "write a memo", "save this as a note", "look up my notes", "記録しておいて", "あとで見返せるようにして", "ナレッジベースに追加", "これメモして", "保存しておいて", "引き継ぎ資料作って", or similar note-taking requests. Also trigger when the user wants to preserve information for later reference, document something important, organize their thoughts in a structured way, or search through their personal knowledge base.
---

# Obsidian Operation Guide

This skill provides the workflow and rules for interacting with an Obsidian vault via the `obsidian` . Following these workflows ensures notes are created consistently with proper templates, tags, and directory placement.

## Basic Knowledge

- CLI command: `obsidian`
- Default vault name: `vault`
- Default vault path: `$HOME/Obsidian/vault`
  - The vault is outside the workspace, so file tools (fsWrite, etc.) cannot access it. Always use `obsidian` commands.

## IMPORTANT: First Command Rule

Run `obsidian help` before the first `obsidian` command in every session. This ensures you have the latest command syntax and available operations - the CLI may have been updated since the skill was written, and this prevents using outdated or incorrect commands.

## Typical Workflows

### Read Existing Note (Unique Name)

**Pre-check**: Confirm `obsidian help` has been executed in this session

1. `obsidian read file=<name>`

### Read Existing Note (Search Required)

**Pre-check**: Confirm `obsidian help` has been executed in this session

1. `obsidian search query=<text>` - Full-text search
2. If no results or too many results, try narrowing:
    - Limit to folder: `obsidian search query=<text> path=<folder>`
    - Search with context: `obsidian search:context query=<text>`
    - Browse by tag: `obsidian tags all counts sort=count` then `obsidian tag name=<tag> verbose`
3. `obsidian read path=<path>` - Read the found note

**Example:**
Input: "前に書いたAWSの設定に関するノートを探して"
1. `obsidian search query="AWS 設定"`
2. Review results, find "AWS Site-to-Site VPN Troubleshooting 2026-02-27"
3. `obsidian read path="3 Notes/AWS Site-to-Site VPN Troubleshooting 2026-02-27.md"`

### Create New Note

**Pre-check**: Confirm `obsidian help` has been executed in this session

1. `obsidian files folder="8 Templates"` - List templates
2. `obsidian read file=<template-name>` - Choose the best suitable template
    - Do not use `Default Template` - it's a fallback with minimal structure; specific templates provide better organization and metadata
    - `Report Template` or `Memo Template` are good for general purpose
3. `obsidian tags all` - List existing tags and choose suitable tags
    - Always include the `generated` tag - this distinguishes AI-generated notes from user-created ones, making it easier to filter and manage automated content
    - Reuse existing tags to maintain consistency and avoid tag proliferation
4. `obsidian create name=<name> path=<folder/name.md> content=<text>`

**Example:**
Input: "引継書を作りたいんだけど、プロジェクトXの設定とか手順をまとめたい"
1. `obsidian files folder="8 Templates"` → Find "Report Template"
2. `obsidian read file="Report Template"` → Review structure
3. `obsidian tags all` → Choose tags: project, memo, handover, generated
4. `obsidian create name="Project X Handover" path="3 Notes/Project X Handover.md" content="---\naliases:\n  - プロジェクトX 引継書\ncreated_at: 2026-03-01T19:00:00+09:00\ncategories: \"[[Projects]]\"\ntags:\n  - project\n  - memo\n  - handover\n  - generated\n---\n\n## Overview\n\n[Project description]\n\n## Setup\n\n[Configuration steps]\n..."`

#### Shell Escaping for `obsidian create`

The `content` value is passed as a shell argument. Use `\n` for newlines and `\t` for tabs (the CLI interprets these). Wrap the value in double quotes and escape inner double quotes with `\"`.

Backticks (`` ` ``) MUST be escaped as `` \` `` — otherwise the shell interprets them as command substitution and silently removes the content between them.

Example:
```
obsidian create name="My Note" path="3 Notes/My Note.md" content="---\naliases:\n  - マイノート\ncreated_at: 2026-03-01T12:00:00+09:00\ncategories: \"[[Memos]]\"\ntags:\n  - yyyy-2026\n  - yyyymm-202603\n  - memo\n  - generated\n---\n\nUse \`obsidian\` to manage notes."
```

## Directory Structure

Directories have specific purposes and access rules. Writing to read-only directories will break the vault's organizational structure.

- `0 Inbox` - Inbox (temporary storage)
- `1 Categories` - Category classification (read-only: categories should not be modified during note creation)
- `2 Daily` - Daily notes (read-only: auto-generated by daily note plugin)
- `3 Notes` - General notes (memos, projects, travel logs, etc.)
- `4 References` - Reference materials (product info, people info, etc.)
- `7 Clippings` - Web clippings (read-only: auto-generated by web clipper)
- `8 Templates` - Templates (read-only: templates should not be modified during note creation)
  - `8 Templates/Bases/` - Bases templates
  - `8 Templates/Web Clipper/` - Web Clipper templates
- `9 Attachments` - Attachments (images, videos, etc.)
- `Library` - Files unrelated to Obsidian (do not access)
- `Snippets` - Snippets files (do not access)

## Title and Filename Standards

- Do not use Heading 1 (`#`) for the title. The filename serves as the title - Obsidian displays the filename as the note title in the UI, so using a Heading 1 would create redundancy and clutter.
- Filenames must be safe across all file systems:
  - Use alphabets, numbers, spaces, and some symbols (such as `-_.`)
  - Add titles with symbols or Japanese titles to the `aliases` property for search purposes - this allows you to use descriptive Japanese names or special characters while keeping the filename filesystem-safe

## Tag

Prefer tags that are already in use on existing notes - this maintains consistency and makes filtering more effective. Avoid adding new tags unless necessary - tag proliferation makes organization harder. Always include the `generated` tag when creating notes - this helps distinguish AI-generated content from user-created notes.

## Related Skills

When working with Obsidian notes, refer to these skills as needed:

- **obsidian-markdown**: For creating and editing Obsidian Flavored Markdown with wikilinks, embeds, callouts, properties, and other Obsidian-specific syntax
- **obsidian-bases**: For creating and editing Obsidian Bases (.base files) with views, filters, formulas, and summaries
- **json-canvas**: For creating and editing JSON Canvas files (.canvas) with nodes, edges, groups, and connections
