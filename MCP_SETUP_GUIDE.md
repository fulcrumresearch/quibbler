# Comprehensive MCP Setup Guide for Quibbler

This guide provides detailed setup instructions for integrating Quibbler with various AI coding assistants via MCP (Model Context Protocol) and Hooks.

## Table of Contents

- [Claude Code](#claude-code)
- [Claude Desktop](#claude-desktop)
- [Cursor](#cursor)
- [Zed](#zed)
- [VS Code](#vs-code)
- [JetBrains IDEs](#jetbrains-ides)
- [iFlow CLI](#iflow-cli)
- [Environment Variables](#environment-variables)
- [Hook Configuration](#hook-configuration)

---

## Claude Code

Claude Code offers the most powerful integration with both MCP and Hooks support.

### MCP Mode Setup

**Configuration Methods:**

1. **Command-line (recommended):**
```bash
claude mcp add quibbler -- quibbler iflow mcp
```

2. **Manual configuration:**

Edit `.claude/settings.json` or `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "quibbler": {
      "command": "quibbler",
      "args": ["iflow", "mcp"],
      "env": {
        "IFLOW_API_KEY": "${IFLOW_API_KEY}",
        "IFLOW_MODEL": "claude-haiku-4-5",
        "QUIBBLER_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Environment Variable Expansion:**

Claude Code supports `${VAR}` and `${VAR:-default}` syntax:

```json
{
  "mcpServers": {
    "quibbler": {
      "command": "quibbler",
      "args": ["iflow", "mcp"],
      "env": {
        "IFLOW_API_KEY": "${IFLOW_API_KEY:-use-default-from-settings}",
        "IFLOW_MODEL": "${QUIBBLER_MODEL:-claude-haiku-4-5}"
      }
    }
  }
}
```

**Scope Hierarchy:**

Claude Code uses three configuration scopes (highest priority first):
1. **Local** (`.claude/settings.local.json`) - Private, not shared
2. **Project** (`.claude/settings.json`) - Shared via Git
3. **User** (`~/.claude/settings.json`) - All projects

### Hook Mode Setup

**1. Start Quibbler Hook Server:**

```bash
quibbler iflow hook server
```

**2. Add Hooks to Project:**

```bash
cd /path/to/your/project
quibbler iflow hook add
```

This creates/updates `.claude/settings.json` with:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [{"type": "command", "command": "quibbler hook notify"}]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {"type": "command", "command": "quibbler hook forward"},
          {"type": "command", "command": "quibbler hook notify"}
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "matcher": "*",
        "hooks": [{"type": "command", "command": "quibbler hook forward"}]
      }
    ],
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "quibbler hook compact-notify",
            "timeout": 120
          }
        ]
      }
    ],
    "Stop": [
      {"hooks": [{"type": "command", "command": "quibbler hook notify"}]}
    ]
  }
}
```

**Available Hook Events:**

| Event | When Triggered | Matcher Support |
|-------|----------------|-----------------|
| `PreToolUse` | Before any tool execution | Yes (tool name) |
| `PostToolUse` | After tool completes | Yes (tool name) |
| `UserPromptSubmit` | User submits prompt | No |
| `PreCompact` | Before context compression | No |
| `Stop` | Agent finishes work | No |
| `SessionStart` | Session begins | No |
| `SessionEnd` | Session ends | No |

**Hook Matchers:**

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",  // Only Write or Edit tools
        "hooks": [...]
      },
      {
        "matcher": "Bash",  // Only Bash tool
        "hooks": [...]
      },
      {
        "matcher": "*",  // All tools
        "hooks": [...]
      }
    ]
  }
}
```

**Environment Variables for Hooks:**

```bash
$CLAUDE_PROJECT_DIR  # Absolute path to project root
$CLAUDE_ENV_FILE     # (SessionStart only) File for persisting variables
```

---

## Claude Desktop

Claude Desktop supports MCP but not hooks.

### Configuration

**File Location:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

**Access via UI:**
Settings → Developer → Edit Config

**Configuration Format:**

```json
{
  "mcpServers": {
    "quibbler": {
      "command": "quibbler",
      "args": ["iflow", "mcp"],
      "env": {
        "IFLOW_API_KEY": "your-api-key-here",
        "IFLOW_MODEL": "claude-haiku-4-5"
      }
    }
  }
}
```

**Using uvx for isolated execution:**

```json
{
  "mcpServers": {
    "quibbler": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/linroger/quibbler-flow.git@claude/quibbler-iflow-cli-01LNU37mzAPUiAP7kqKHiWeq",
        "quibbler",
        "iflow",
        "mcp"
      ],
      "env": {
        "IFLOW_API_KEY": "your-api-key"
      }
    }
  }
}
```

**Important Notes:**
- Must completely quit and restart Claude Desktop for changes to take effect
- Environment variable expansion not supported (use literal values)
- No hooks support

---

## Cursor

Cursor supports MCP via `.cursor/mcp.json` configuration.

### Configuration

**File Locations:**
- **Project**: `.cursor/mcp.json` (in project root)
- **Global**: `~/.cursor/mcp.json` (user home directory)

**Basic Configuration:**

```json
{
  "mcpServers": {
    "quibbler": {
      "command": "quibbler",
      "args": ["iflow", "mcp"],
      "env": {
        "IFLOW_API_KEY": "your-api-key-here",
        "IFLOW_MODEL": "claude-haiku-4-5"
      }
    }
  }
}
```

**Using npx:**

```json
{
  "mcpServers": {
    "quibbler": {
      "command": "npx",
      "args": ["-y", "quibbler-flow@latest", "iflow", "mcp"],
      "env": {
        "IFLOW_API_KEY": "your-key"
      }
    }
  }
}
```

### Environment Variable Workaround

Cursor doesn't natively support `${VAR}` expansion. Use `envmcp`:

**1. Install envmcp:**

```bash
npm install -g envmcp
```

**2. Create `.env` file:**

```bash
IFLOW_API_KEY=your-api-key-here
IFLOW_MODEL=claude-haiku-4-5
```

**3. Configure with envmcp:**

```json
{
  "mcpServers": {
    "quibbler": {
      "command": "npx",
      "args": [
        "envmcp",
        "quibbler",
        "iflow",
        "mcp"
      ]
    }
  }
}
```

**Important Notes:**
- No hooks support
- Environment variables must be hardcoded or use envmcp workaround
- Restart Cursor after config changes

**Sources:**
- [Cursor MCP Documentation](https://docs.cursor.com/context/model-context-protocol)
- [Cursor Forum: Environment Variables](https://forum.cursor.com/t/how-to-use-environment-variables-in-mcp-json/79296)

---

## Zed

Zed Editor supports MCP via context servers.

### Configuration

**File Locations:**
- **Project**: `.zed/settings.json`
- **Global**: `~/.config/zed/settings.json`

**Configuration Format:**

```json
{
  "context_servers": {
    "quibbler": {
      "command": {
        "path": "quibbler",
        "args": ["iflow", "mcp"],
        "env": {
          "IFLOW_API_KEY": "your-api-key",
          "IFLOW_MODEL": "claude-haiku-4-5"
        }
      }
    }
  }
}
```

**Alternative format:**

```json
{
  "context_servers": {
    "quibbler": {
      "command": "quibbler",
      "args": ["iflow", "mcp"],
      "env": {
        "IFLOW_API_KEY": "your-key"
      }
    }
  }
}
```

**Adding via UI:**

1. Open Agent Panel
2. Click "Add Custom Server"
3. Enter server details

**Server Status:**
- Green dot = Active
- Red dot = Issues (check logs)

**Important Notes:**
- Uses `context_servers` instead of `mcpServers`
- No hooks support when using Claude Code with Zed
- Environment variables in `env` object are supported

**Sources:**
- [Model Context Protocol in Zed](https://zed.dev/docs/ai/mcp)

---

## VS Code

VS Code has full MCP support since v1.102.

### Configuration

**Methods:**

1. **Via Chat Interface:**
   - Click 'Add More Tools...'
   - Select 'Add MCP Server'
   - Choose 'NPX Package'

2. **Via Settings:**

```json
{
  "mcpServers": {
    "quibbler": {
      "command": "quibbler",
      "args": ["iflow", "mcp"],
      "env": {
        "IFLOW_API_KEY": "your-api-key"
      }
    }
  }
}
```

**Using npx:**

```json
{
  "mcpServers": {
    "quibbler": {
      "command": "npx",
      "args": ["-y", "quibbler-flow", "iflow", "mcp"],
      "env": {
        "IFLOW_API_KEY": "${env:IFLOW_API_KEY}"
      }
    }
  }
}
```

**Features:**
- Full MCP specification support
- Tools, Prompts, Resources, Sampling
- Environment variable support

**Sources:**
- [Use MCP servers in VS Code](https://code.visualstudio.com/docs/copilot/chat/mcp-servers)

---

## JetBrains IDEs

JetBrains IDEs (IntelliJ, PyCharm, WebStorm, etc.) support MCP via proxy.

### Configuration

**Built-in MCP Server (v2025.2+):**

Settings → Tools → MCP Server

**Connecting External Clients:**

```json
{
  "mcpServers": {
    "quibbler": {
      "command": "npx",
      "args": ["-y", "@jetbrains/mcp-proxy"],
      "env": {
        "IDE_PORT": "port-number"
      }
    }
  }
}
```

**Enable External Connections:**

Settings → Tools → MCP Server → "Can accept external connections"

**Sources:**
- [MCP Server in IntelliJ IDEA Documentation](https://www.jetbrains.com/help/idea/mcp-server.html)

---

## iFlow CLI

iFlow CLI is the primary target for the enhanced Quibbler version.

### Configuration

**File Locations:**
- **Global**: `~/.iflow/mcp.json`
- **Project**: `.iflow/mcp.json`

**Basic Configuration:**

```json
{
  "mcpServers": {
    "quibbler": {
      "command": "quibbler",
      "args": ["iflow", "mcp"]
    }
  }
}
```

**With Environment Variables:**

```json
{
  "mcpServers": {
    "quibbler": {
      "command": "quibbler",
      "args": ["iflow", "mcp"],
      "env": {
        "IFLOW_MODEL": "claude-sonnet-4-5",
        "QUIBBLER_AUTO_SUMMARY": "true",
        "QUIBBLER_SMART_TRIGGERS": "true",
        "QUIBBLER_AUTO_COMPACT": "true",
        "QUIBBLER_COMPACT_THRESHOLD": "0.75"
      }
    }
  }
}
```

**Using iflow CLI:**

```bash
iflow mcp add-json '{"quibbler": {"command": "quibbler", "args": ["iflow", "mcp"]}}'
```

### Hook Mode (if supported)

**Check if iFlow supports hooks:**

Refer to [iFlow CLI documentation](https://platform.iflow.cn/en/cli/configuration/settings) for latest hook support.

**If supported, configure similarly to Claude Code:**

```bash
quibbler iflow hook add
```

**Sources:**
- [MCP | iFlow Platform](https://platform.iflow.cn/en/cli/examples/mcp)
- [CLI Configuration | iFlow Platform](https://platform.iflow.cn/en/cli/configuration/settings)

---

## Environment Variables

Quibbler supports various environment variables for configuration.

### General Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `IFLOW_API_KEY` | iFlow API key (optional if logged in) | From `~/.iflow/settings.json` | `sk-xxx...` |
| `IFLOW_BASE_URL` | iFlow API base URL | `https://apis.iflow.cn/v1` | Custom URL |
| `IFLOW_MODEL` | Model to use | `claude-haiku-4-5` | `claude-sonnet-4-5` |
| `IFLOW_AUTH_TYPE` | Authentication type | `iflow` | `openai-compatible` |

### Quibbler-Specific Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `QUIBBLER_AUTO_SUMMARY` | Enable auto-summarization | `true` | `true`/`false` |
| `QUIBBLER_SMART_TRIGGERS` | Enable smart event filtering | `true` | `true`/`false` |
| `QUIBBLER_AUTO_COMPACT` | Enable auto-compaction at threshold | `true` | `true`/`false` |
| `QUIBBLER_COMPACT_THRESHOLD` | Context % to trigger compaction | `0.75` (75%) | `0.70`-`0.85` |
| `QUIBBLER_TEMPERATURE` | Sampling temperature | `0.7` | `0.0`-`1.0` |
| `QUIBBLER_MAX_TOKENS` | Max tokens per response | `None` (unlimited) | `4096`, `8192` |
| `QUIBBLER_LOG_LEVEL` | Logging level | `INFO` | `DEBUG`, `WARNING` |
| `QUIBBLER_MONITOR_BASE` | Hook server URL | `http://127.0.0.1:8082` | Custom URL |

### Configuration File vs Environment Variables

**Priority (highest to lowest):**
1. Environment variables
2. Project config (`.quibbler/iflow_config.json`)
3. Global config (`~/.quibbler/iflow_config.json`)
4. Defaults

**Example using all methods:**

**Environment:**
```bash
export IFLOW_MODEL="claude-sonnet-4-5"
export QUIBBLER_COMPACT_THRESHOLD="0.70"
```

**Global config** (`~/.quibbler/iflow_config.json`):
```json
{
  "model": "claude-haiku-4-5",
  "enable_auto_summary": true,
  "enable_smart_triggers": true,
  "enable_auto_compact": true,
  "compact_threshold": 0.75,
  "temperature": 0.7,
  "max_tokens": null
}
```

**Project config** (`.quibbler/iflow_config.json`):
```json
{
  "model": "claude-haiku-4-5",
  "compact_threshold": 0.80
}
```

**Result:** Model from env var (`sonnet`), threshold from env var (`0.70`), other settings from config files.

---

## Hook Configuration

Detailed hook configuration for platforms that support it.

### Claude Code Hooks (Full Support)

**Auto-Compaction Hook:**

Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "quibbler hook pre-compact",
            "timeout": 120
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "quibbler hook forward"
          },
          {
            "type": "command",
            "command": "quibbler hook notify"
          }
        ]
      }
    ]
  }
}
```

**Custom Hook Script:**

Create `.claude/hooks/quibbler-check.sh`:

```bash
#!/bin/bash
# Auto-trigger Quibbler review on Write/Edit

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool')
PROJECT_DIR="$CLAUDE_PROJECT_DIR"

if [[ "$TOOL" == "Write" ]] || [[ "$TOOL" == "Edit" ]]; then
  echo "Triggering Quibbler review..." >&2
  curl -X POST http://127.0.0.1:8082/hook/$(echo "$INPUT" | jq -r '.session_id') \
    -H "Content-Type: application/json" \
    -d "$INPUT" \
    2>&1 > /dev/null
fi

exit 0
```

Make executable:
```bash
chmod +x .claude/hooks/quibbler-check.sh
```

Add to `.claude/settings.json`:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/quibbler-check.sh",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

### iFlow Hooks (If Supported)

**Check official documentation for latest hook support:**

[iFlow CLI Changelog](https://platform.iflow.cn/en/cli/changelog)

**If hooks are supported:**

```bash
quibbler iflow hook add
```

This creates `.iflow/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [...],
    "PostToolUse": [...],
    "UserPromptSubmit": [...],
    "Stop": [...]
  }
}
```

---

## Platform Comparison Matrix

| Feature | Claude Code | Claude Desktop | Cursor | Zed | VS Code | JetBrains | iFlow CLI |
|---------|-------------|----------------|--------|-----|---------|-----------|-----------|
| **MCP Support** | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Via Proxy | ✅ Full |
| **Hooks** | ✅ Full | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No | ⚠️ Check docs |
| **Env Vars** | ✅ `${VAR}` | ⚠️ Limited | ⚠️ Literal | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Config Scopes** | 3 levels | 1 level | 2 levels | 2 levels | 1 level | Settings | 2 levels |
| **Auto-compact** | ✅ Hooks | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ If hooks |

---

## Best Practices

### Security

1. **Never commit API keys** to version control
2. Use environment variables or `settings.local.json`
3. Use `${VAR:-default}` syntax when available
4. Review hook scripts for injection vulnerabilities

### Performance

1. Use `claude-haiku-4-5` for fast reviews (default)
2. Enable auto-compaction to prevent context overflow
3. Set `compact_threshold` between 0.70-0.80 for optimal balance
4. Use smart triggers in hook mode to reduce API calls

### Reliability

1. Set appropriate hook timeouts (60-120s for review operations)
2. Test hook scripts in isolation before deploying
3. Monitor `~/.quibbler/quibbler.log` for issues
4. Use health check endpoint to verify hook server status

---

## Troubleshooting

### "quibbler: command not found"

Ensure quibbler is installed and in PATH:

```bash
which quibbler
# If not found:
uv tool install /path/to/quibbler-flow
```

### Environment variables not working

**Claude Code:** Use `${VAR}` syntax
**Cursor:** Use `envmcp` workaround
**Claude Desktop:** Use literal values
**Others:** Check platform-specific documentation

### Hooks not triggering

1. Check hook server is running:
   ```bash
   curl http://127.0.0.1:8082/health
   ```

2. Verify hook configuration:
   ```bash
   cat .claude/settings.json | jq '.hooks'
   ```

3. Check logs:
   ```bash
   tail -f ~/.quibbler/quibbler.log
   ```

### Context compaction not working

Check configuration:

```bash
cat ~/.quibbler/iflow_config.json
```

Ensure:
```json
{
  "enable_auto_compact": true,
  "compact_threshold": 0.75
}
```

---

## Additional Resources

- [Claude Code MCP Documentation](https://code.claude.com/docs/en/mcp)
- [Claude Code Hooks Guide](https://code.claude.com/docs/en/hooks-guide)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [iFlow CLI Documentation](https://platform.iflow.cn/en/cli/)
- [Cursor MCP Guide](https://docs.cursor.com/context/model-context-protocol)
- [Zed MCP Guide](https://zed.dev/docs/ai/mcp)
- [VS Code MCP Guide](https://code.visualstudio.com/docs/copilot/chat/mcp-servers)
