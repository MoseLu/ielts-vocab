# Agent Browser Guide

## Purpose

Use Agent Browser for fast browser automation and page inspection during local debugging.

This guide is intentionally short. It focuses on the commands and workflows that are useful for this repository instead of duplicating the full upstream command reference.

## Current Setup

- Agent Browser is installed globally.
- Chrome for Testing is available for local runs.
- Playwright MCP is also available for more complex browser workflows.

## Core Workflow

1. Open the local app:

```bash
agent-browser open http://127.0.0.1:3002
```

2. Capture a snapshot to get interactive element references:

```bash
agent-browser snapshot
```

3. Interact with elements using the returned `@e...` references:

```bash
agent-browser click @e1
agent-browser type @e2 "example text"
```

4. Capture a screenshot when layout verification matters:

```bash
agent-browser screenshot
```

## Useful Commands

```bash
agent-browser open <url>
agent-browser back
agent-browser forward
agent-browser refresh
agent-browser snapshot
agent-browser click <ref>
agent-browser type <ref> <text>
agent-browser select <ref> <value>
agent-browser screenshot
agent-browser info
agent-browser get <ref>
agent-browser session list
```

## Repository-Specific Tips

- Prefer `http://127.0.0.1:3002` when checking the Vite dev server directly.
- If the issue may involve the full proxy chain, test through `https://axiomaticworld.com` as a second pass.
- Always re-run `snapshot` after navigation or dynamic UI changes so references stay current.
- Use screenshots for AI chat, journal, and stats pages where layout regressions matter more than plain DOM state.

## When to Use Playwright Instead

Use Playwright MCP when you need:

- multi-step flows with assertions
- richer DOM querying
- reusable E2E scripts
- browser-context setup or teardown across many pages

Use Agent Browser when you need:

- quick manual exploration
- fast page inspection
- low-overhead navigation and screenshots

## Troubleshooting

### Browser not available

Reinstall the browser bundle:

```bash
agent-browser install --with-deps
```

### Element reference stopped working

The page probably changed. Run:

```bash
agent-browser snapshot
```

### Proxy-specific issue

Compare both paths:

```bash
agent-browser open http://127.0.0.1:3002
agent-browser open https://axiomaticworld.com
```
