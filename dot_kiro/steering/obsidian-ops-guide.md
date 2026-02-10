# Obsidian Operation Guide

- When accessing Obsidian, you SHOULD use `obsidian` command.
- vault name is `vault`.
- vault path is `$HOME/Obsidian/vault`

## IMPORTANT: First Command Rule

You MUST run `obsidian help vault=vault` BEFORE the FIRST `obsidian` command. This ensures you have the latest command syntax and available operations.

## Typical Workflows

### Read Existing Note (Unique Name)

**Pre-check:**: Confirm `obsidian help vault=vault` has been executed in this session

1. `obsidian read file=<name> vault=vault`

### Read Existing Note (Search Required)

**Pre-check:**: Confirm `obsidian help vault=vault` has been executed in this session

1. `obsidian search query=<text> vault=vault`
2. `obsidian read path=<path> vault=vault`

### Create New Note

When creating new notes, you MUST follow this workflow:

**Pre-check:**: Confirm `obsidian help vault=vault` has been executed in this session

1. `obsidian files folder="8 Templates" vault=vault` - List templates
2. `obsidian read file=<template-name> vault=vault` - Read a template
3. `obsidian tags all vault=vault` - List existing tags
4. `obsidian create [name=<name>] [path=<path>] [content=<text>] vault=vault`

You MUST NOT skip the template selection step.

## Directory Structure

- `0 Inbox` - Inbox (temporary storage)
- `1 Categories` - Category classification. You MUST NOT write in this directory
- `2 Daily` - Daily notes. You MUST NOT write in this directory
- `3 Notes` - General notes (memos, projects, travel logs, etc.)
- `4 References` - Reference materials (product info, people info, etc.)
- `7 Clippings` - Web clippings. You MUST NOT write in this directory
- `8 Templates` - Templates. You MUST NOT write in this directory
  - `8 Templates/Bases/` - Bases templates
  - `8 Templates/Web Clipper/` - Web Clipper templates
- `9 Attachments` - Attachments (images, videos, etc.)
- `Library` - Files unrelated to Obsidian. You MUST NOT read/write in this directory
- `Snippets` - Snippets Files. You MUST NOT read/write in this directory

## Title and Filename Standards

- You MUST not use Heading 1 (#) for the title. Instead, you MUST write the title as the filename.
- You MUST follow these rules for filename to be safe across all file systems:
  - Use alphabets, numbers, spaces, and some symbols (such as `-_.`)
  - You MAY add titles with symbols or Japanese titles to the `aliases` property for search purposes

## Template

When creating a new note, you MUST choose a template from `8 Templates/` directory.

## Tag

You SHOULD use tags that are already in use on existing notes and avoid adding new tags.
