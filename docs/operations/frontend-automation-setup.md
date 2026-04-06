# Frontend Automation Setup

## Purpose

This document describes the local browser-automation stack used by the project and when to use each layer.

## Tooling Stack

### Agent Browser

Use for quick local browser automation, snapshots, and screenshots.

### Playwright MCP

Use for richer browser workflows driven through the coding agent.

### Playwright Test

Use for repeatable E2E test runs from the repository itself.

## Recommended Usage

### Fast local inspection

Use Agent Browser:

```bash
agent-browser open http://127.0.0.1:3002
agent-browser snapshot
```

### Agent-driven multi-step browser work

Use Playwright MCP through the coding assistant.

### Repeatable regression coverage

Run Playwright tests from the repository:

```bash
pnpm exec playwright test
pnpm exec playwright test --headed
pnpm exec playwright test --ui
```

## Local Prerequisites

1. Start the backend:

```bash
cd backend
python app.py
```

2. Start the frontend:

```bash
pnpm dev
```

3. If needed, also verify the proxy path:

```text
https://axiomaticworld.com -> natapp -> local :80 -> nginx -> local :3002
```

## Practical Guidance

- Use Agent Browser first when the task is exploratory.
- Use Playwright MCP when the workflow spans multiple pages or needs stronger assertions.
- Use Playwright Test when the scenario should become a durable regression test.
- Keep screenshots and one-off artifacts out of `docs/` unless they are long-lived references.

## Troubleshooting

### Browser install missing

```bash
agent-browser install --with-deps
pnpm exec playwright install chromium
```

### Port conflict

Make sure the frontend still binds to `3002`, or stop the conflicting process before running browser checks.

### Proxy-only failures

If local Vite works but the public tunnel path fails, investigate the nginx or natapp layer before changing frontend code.
