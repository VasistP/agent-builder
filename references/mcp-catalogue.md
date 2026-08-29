# Recommended MCP servers for agent development

Wired into `templates/.mcp.json` by `skills/1-scaffold`. All optional but
recommended; each entry in the file has a one-line comment. These enhance the
*development* workflow — they are not runtime dependencies of the agent.

| MCP | Purpose | Why it helps here | Install |
|-----|---------|-------------------|---------|
| **context7** | Up-to-date library / framework documentation on demand | Stops the dev agent guessing stale APIs for LangGraph, OTel, the model SDK, vector DB clients. Use it in `skills/1`, `5`, `6` before writing framework code. | `npx -y @upstash/context7-mcp` |
| **playwright** | Browser automation | E2E-test any dashboard UI; drive web apps the agent must interact with; capture screenshots for checkpoint reviews. | `npx -y @playwright/mcp` |
| **memory** | Persistent knowledge-graph memory across sessions | The build spans many checkpoints/sessions; store decisions, the spec summary, per-feature context so a fresh session (or subagent) doesn't re-derive it. Complements `.agentbuilder/`. | `npx -y @modelcontextprotocol/server-memory` |
| **sequential-thinking** | Structured multi-step reasoning tool | Helps during complex planning (graph design in `skills/5`, tricky features in `skills/6`, audit triage). | `npx -y @modelcontextprotocol/server-sequential-thinking` |

## `.mcp.json` shape

```jsonc
{
  "mcpServers": {
    // Current docs for any library — query before writing framework code.
    "context7": { "command": "npx", "args": ["-y", "@upstash/context7-mcp"] },
    // Browser automation for dashboard E2E and web-interacting agents.
    "playwright": { "command": "npx", "args": ["-y", "@playwright/mcp"] },
    // Cross-session memory of decisions/spec/feature context.
    "memory": { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory"] },
    // Structured step-by-step reasoning for complex planning.
    "sequential-thinking": { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"] }
  }
}
```

## Notes

- Some MCP servers need auth or a separate install step; tell the user and let
  them enable in an interactive session (`claude mcp` / `/mcp`).
- If the agent itself needs to call tools that happen to be MCP servers (e.g. a
  database MCP), that is a runtime concern handled in the spec + tool registry,
  not this dev-time list.
