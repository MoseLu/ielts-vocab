# Agent-Browser Guide for IELTS Vocabulary App

## Overview

We have installed **Agent-Browser** (v0.22.3), a Rust-based headless browser automation CLI designed specifically for AI agents.

## Installation Status

✅ **Agent-Browser** installed globally: `agent-browser 0.22.3`
✅ **Chrome for Testing** downloaded and ready
✅ **Playwright MCP** installed: `@playwright/mcp v0.0.68`

## Agent-Browser Commands

### Basic Usage

```bash
# Navigate to a URL
agent-browser open http://localhost:5173

# Take a snapshot (get interactive elements)
agent-browser snapshot

# Click an element by reference
agent-browser click @e1

# Type into an input
agent-browser type @e2 "Hello World"

# Take a screenshot
agent-browser screenshot

# Get page information
agent-browser info
```

### Common Commands

```bash
# Navigation
agent-browser open <url>              # Open URL
agent-browser back                     # Go back
agent-browser forward                  # Go forward
agent-browser refresh                  # Refresh page

# Interaction
agent-browser click <ref>             # Click element
agent-browser type <ref> <text>       # Type text
agent-browser select <ref> <value>     # Select from dropdown

# Inspection
agent-browser snapshot                 # Get element references
agent-browser screenshot                # Capture screenshot
agent-browser info                     # Page information
agent-browser get <ref>               # Get element details

# Forms
agent-browser fill <json>              # Fill form with JSON

# Session
agent-browser session list             # List sessions
agent-browser session save <name>      # Save session
agent-browser session load <name>      # Load session
```

## Usage with Claude Code

### Method 1: Direct CLI Usage

```bash
# Open the app
agent-browser open http://localhost:5173

# Take a snapshot to get element references
agent-browser snapshot

# Interact with elements (use @e1, @e2, etc. from snapshot)
agent-browser click @e1
```

### Method 2: Through Playwright MCP

The **Playwright MCP** server is configured and available through Claude Code. You can ask Claude to:

- "Open http://localhost:5173 with Playwright"
- "Click on the login button"
- "Take a screenshot of the page"
- "Fill in the login form"
- "Navigate through all pages"

## Testing Your App

### Test Login Flow

```bash
# Open the app
agent-browser open http://localhost:5173

# Wait for redirect to login
agent-browser snapshot

# Fill login form (adjust element references based on snapshot)
agent-browser type @e1 "testuser"
agent-browser type @e2 "password123"
agent-browser click @e3
```

### Test Practice Page

```bash
# Navigate to practice
agent-browser open http://localhost:5173/practice

# Take snapshot
agent-browser snapshot

# Click on practice mode selector
agent-browser click @e1

# Select a mode
agent-browser click @e5
```

## Benefits of Agent-Browser

1. **Fast**: Rust-based, launches in <50ms
2. **Efficient**: Uses element references (@e1, @e2) instead of full DOM trees
3. **Context-friendly**: Reduces token usage by 93% compared to traditional tools
4. **108+ commands**: Covers navigation, interaction, inspection, media, and more
5. **Cross-platform**: Works on macOS, Linux, and Windows

## Comparison: Agent-Browser vs Playwright MCP

| Feature | Agent-Browser | Playwright MCP |
|---------|--------------|----------------|
| Primary Use | CLI-based automation | MCP server integration |
| Performance | Extremely fast (Rust) | Fast (Node.js) |
| Token Usage | Minimal (references) | Moderate |
| Integration | Direct CLI | Through Claude Code |
| Commands | 108+ | Standard Playwright API |
| Best For | Quick CLI tasks | Complex workflows |

## Tips for Best Results

1. **Always take snapshots first**: Use `agent-browser snapshot` to get element references
2. **Wait for dynamic content**: Use `agent-browser wait` or add delays
3. **Save sessions**: Use `agent-browser session save` to reuse state
4. **Use screenshots**: Take screenshots at key steps for debugging
5. **Test in small chunks**: Break complex flows into smaller steps

## Troubleshooting

### "Chrome not found"
```bash
agent-browser install --with-deps
```

### Permission denied (Windows)
```bash
# Run as administrator or adjust permissions
```

### Element not found
```bash
# Take a new snapshot to get updated references
agent-browser snapshot
```

## Next Steps

1. **Explore**: Use `agent-browser snapshot` to explore your app
2. **Automate**: Create scripts for common testing workflows
3. **Integrate**: Use with Claude Code for AI-assisted testing
4. **Scale**: Combine with E2E tests for comprehensive coverage

## Resources

- [Agent-Browser GitHub](https://github.com/vercel-labs/agent-browser)
- [Agent-Browser Skills](https://agent-browser.dev/skills)
- [Playwright MCP](https://www.npmjs.com/package/@playwright/mcp)
- [E2E Tests](./tests/e2e/README.md)
