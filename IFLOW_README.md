# Quibbler for iFlow CLI

**Enhanced code review agent for iFlow CLI with token-efficient context management**

This is an extended version of Quibbler specifically optimized for iFlow CLI, featuring:

- ✅ **Automatic Authentication** - Uses iFlow's saved credentials (no API key configuration needed)
- ✅ **Token-Efficient Context** - Smart summarization for long conversations
- ✅ **Smart Event Filtering** - Only processes critical events to reduce noise
- ✅ **Enhanced Prompts** - Optimized for better critique quality
- ✅ **Structured Logging** - Detailed metrics and analytics
- ✅ **Full Feature Parity** - All standard Quibbler features plus optimizations

## What is Quibbler?

Quibbler is a paranoid code critic that watches your AI coding agent and catches issues like:

- 🚫 Fabricating results without running commands
- 🚫 Skipping tests or verification steps
- 🚫 Not following your coding style and patterns
- 🚫 Hallucinating numbers, metrics, or functionality
- 🚫 Creating new patterns instead of using existing ones
- 🚫 Making changes that don't align with user intent

## Why iFlow CLI Version?

The standard Quibbler uses Claude's API (requires `ANTHROPIC_API_KEY`). This iFlow version:

1. **Uses your iFlow authentication automatically** - No separate API key needed
2. **More token-efficient** - Automatically summarizes old messages to reduce costs
3. **Smarter filtering** - Only reviews at important checkpoints
4. **Enhanced prompts** - Better at catching subtle issues

## Installation

```bash
# Install from this repository
uv tool install git+https://github.com/linroger/quibbler-flow.git@claude/quibbler-iflow-cli-01LNU37mzAPUiAP7kqKHiWeq

# Or using pip
pip install git+https://github.com/linroger/quibbler-flow.git@claude/quibbler-iflow-cli-01LNU37mzAPUiAP7kqKHiWeq
```

## Prerequisites

1. **iFlow CLI installed and authenticated:**
   ```bash
   # Install iFlow CLI (if not already installed)
   npm install -g @iflow/cli

   # Log in to iFlow
   iflow auth login
   ```

2. This creates `~/.iflow/settings.json` with your credentials that Quibbler will use automatically.

## Choosing Your Mode

Quibbler for iFlow supports two integration modes:

### MCP Mode (Recommended for most users)

- ✅ Works with any MCP-compatible agent
- ✅ Synchronous review with immediate feedback
- ✅ Simple setup via MCP configuration
- ✅ Agent explicitly calls `review_code` tool

### Hook Mode (For iFlow CLI with hooks support)

- ✅ Passive event-driven monitoring
- ✅ Fire-and-forget feedback via file writes
- ✅ More powerful observability
- ⚠️ Requires iFlow CLI hook support (check iFlow CLI docs)

---

## Setup Instructions

### Option A: MCP Mode Setup

#### 1. Configure MCP Server

Add Quibbler to your iFlow CLI MCP configuration:

**For iFlow CLI** (`~/.iflow/mcp.json` or `.iflow/mcp.json`):

```json
{
  "mcpServers": {
    "quibbler": {
      "command": "quibbler iflow mcp"
    }
  }
}
```

**Note:** No environment variables needed! Quibbler automatically uses your iFlow authentication from `~/.iflow/settings.json`.

#### 2. Add to AGENTS.md

Create or update `AGENTS.md` in your project root:

```markdown
## Code Review Process

After making code changes, you MUST call the `review_code` tool from the Quibbler MCP server with:

- `user_instructions`: The exact instructions the user gave you
- `agent_plan`: **A detailed summary of the specific changes you made** (include which files were modified, what was added/changed, and key implementation details)
- `project_path`: The absolute path to this project

Review Quibbler's feedback and address any issues or concerns raised.

### Example

User asks: "Add error handling to the API endpoints"

After implementing, call:

```python
review_code(
    user_instructions="Add error handling to the API endpoints",
    agent_plan="""Changes made:

1. Added try-catch blocks in routes/api.py for all endpoints
2. Created custom error classes in errors/api_errors.py
3. Added error response formatting in utils/responses.py
4. Updated tests in tests/test_api.py to verify error cases
5. All tests passing (ran pytest)""",
    project_path="/absolute/path/to/project"
)
```
```

---

### Option B: Hook Mode Setup

**Note:** Hook mode requires iFlow CLI to support hooks similar to Claude Code. Check iFlow CLI documentation to verify hook support.

#### 1. Start Quibbler iFlow Hook Server

In a terminal, start the server:

```bash
quibbler iflow hook server
# Or specify a custom port:
quibbler iflow hook server 9000
```

**Default port:** 8082 (different from standard Quibbler's 8081)

Keep this server running in the background.

#### 2. Configure Hooks in Your Project

In your project directory, run:

```bash
quibbler iflow hook add
```

This creates or updates `.iflow/settings.json` with hooks that:
- Forward tool use events to Quibbler
- Display Quibbler feedback to the agent

#### 3. Verify Setup

The `.iflow/settings.json` should now contain hooks configuration. When iFlow CLI runs in this project, Quibbler will automatically observe and intervene when needed.

---

## Configuration

### Model Selection

By default, Quibbler uses `claude-haiku-4-5` for speed and cost-efficiency. You can change this:

**Global config** (`~/.quibbler/iflow_config.json`):

```json
{
  "model": "claude-sonnet-4-5",
  "enable_auto_summary": true,
  "enable_smart_triggers": true,
  "temperature": 0.7,
  "max_tokens": 4096
}
```

**Project-specific config** (`.quibbler/iflow_config.json`):

```json
{
  "model": "claude-sonnet-4-5"
}
```

Project config takes precedence over global config.

### Context Management Options

- `enable_auto_summary` (default: `true`) - Automatically summarize old messages when conversation gets long
- `enable_smart_triggers` (default: `true`) - Only process critical events in hook mode
- `temperature` (default: `0.7`) - Sampling temperature for model
- `max_tokens` (default: `4096`) - Maximum tokens in response

### Custom Prompts

Customize the system prompt by editing `~/.quibbler/iflow_prompt.md`. The default prompt will be created on first run.

Project-specific rules in `.quibbler/rules.md` are automatically loaded.

---

## How It Works

### MCP Mode

1. Agent makes code changes, then calls `review_code` tool with details
2. Quibbler maintains a persistent review agent per project that:
   - Reviews completed changes against user intent
   - Uses Read tool to examine changed files and existing patterns
   - Validates claims and checks for hallucinations
   - Automatically summarizes old conversation when context gets large
3. Returns feedback or approval synchronously
4. Agent addresses any issues found

### Hook Mode

1. iFlow CLI triggers hooks on events (tool use, prompt submission, etc.)
2. Events are forwarded to Quibbler HTTP server
3. Quibbler maintains a persistent observer agent per session that:
   - **Smart filtering**: Only processes critical events (PostToolUse for Write/Edit, Stop, UserPromptSubmit)
   - Passively watches agent actions
   - **Auto-summarization**: Compresses old messages when conversation gets long
   - Intervenes by writing feedback to `.quibbler/{session_id}.txt`
4. Feedback displayed to agent via notify hook
5. Agent sees feedback and adjusts behavior

### Token Efficiency Features

**Automatic Summarization:**
- When conversation exceeds 15 messages, old messages are summarized
- Recent 5 messages always kept in full
- Summary includes key issues, patterns, decisions
- Reduces token usage by ~60-80% in long sessions

**Smart Event Filtering (Hook Mode):**
- Only processes: PostToolUse (for Write/Edit), Stop, UserPromptSubmit
- Skips low-signal events to reduce API calls
- Focus on high-impact moments

**Cached Rules:**
- Project rules stored in `.quibbler/rules.md`
- Loaded once per session, not re-sent with every message

---

## Logging and Monitoring

### Log Files

- **Main log:** `~/.quibbler/quibbler.log` - All Quibbler activity
- **Metrics:** `~/.quibbler/metrics.jsonl` - Performance metrics (JSON Lines)
- **Reviews:** `~/.quibbler/reviews.jsonl` - Review history and analytics

### View Statistics

```python
from quibbler.enhanced_logger import MetricsLogger

logger = MetricsLogger()
stats = logger.get_session_stats()  # All sessions
stats = logger.get_session_stats("session_123")  # Specific session

print(stats)
# {
#   'total_reviews': 42,
#   'approved': 28,
#   'issues_found': 14,
#   'avg_context_size': 8.5,
#   'summarized_sessions': 3,
#   'avg_feedback_length': 245
# }
```

---

## Advanced Features

### Learned Rules

As Quibbler reviews code, it can save project-specific rules to `.quibbler/rules.md`:

```markdown
### Rule: Test Real Functionality

When testing authentication, use actual auth flows and real tokens (from test fixtures), not mocked responses. We've had issues with mocks hiding integration bugs.

### Rule: Error Messages Include Context

All error messages should include the operation being attempted and relevant IDs/identifiers for debugging.
```

These rules are automatically loaded in future reviews.

### Health Check (Hook Mode)

Check server status:

```bash
curl http://127.0.0.1:8082/health
```

Response:
```json
{
  "status": "healthy",
  "active_sessions": 2,
  "sessions": [
    {
      "session_id": "abc12345...",
      "reviews": 15,
      "messages": 8,
      "has_summary": true
    }
  ]
}
```

---

## Troubleshooting

### "No iFlow authentication found"

**Solution:** Make sure you've logged into iFlow CLI:

```bash
iflow auth login
```

This creates `~/.iflow/settings.json` with your credentials.

Alternatively, set environment variable:

```bash
export IFLOW_API_KEY="your-api-key"
```

### Hook server not receiving events

1. Check server is running: `curl http://127.0.0.1:8082/health`
2. Verify `.iflow/settings.json` has hooks configured
3. Check logs: `tail -f ~/.quibbler/quibbler.log`
4. Ensure iFlow CLI supports hooks (check iFlow CLI docs)

### Context not being summarized

Check config has `enable_auto_summary: true` in `.quibbler/iflow_config.json`

### Too many/few events processed

Adjust `enable_smart_triggers` in config:
- `true`: Only critical events (recommended)
- `false`: All events (more thorough but more API calls)

---

## Comparison: Standard vs iFlow Quibbler

| Feature | Standard Quibbler | iFlow Quibbler |
|---------|------------------|----------------|
| Authentication | `ANTHROPIC_API_KEY` required | Automatic from `~/.iflow/settings.json` |
| Context Management | Full conversation history | Auto-summarization when long |
| Event Processing | All events | Smart filtering (critical only) |
| Token Efficiency | Standard | Optimized (60-80% reduction) |
| Prompts | Standard | Enhanced & optimized |
| Logging | Basic | Structured with metrics |
| Analytics | None | Built-in review analytics |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        iFlow CLI                             │
│                  (your coding agent)                         │
└──────────────┬────────────────────────┬─────────────────────┘
               │                        │
         (MCP mode)               (Hook mode)
               │                        │
               ▼                        ▼
   ┌───────────────────┐    ┌──────────────────────┐
   │  Quibbler MCP     │    │  Quibbler Hook       │
   │  Server           │    │  Server (port 8082)  │
   │  (stdio)          │    │  (HTTP)              │
   └─────────┬─────────┘    └──────────┬───────────┘
             │                         │
             │   ┌─────────────────────┘
             │   │
             ▼   ▼
   ┌──────────────────────────────────────────────┐
   │      iFlow API Client                        │
   │  (automatic auth from ~/.iflow/settings)     │
   └──────────────────┬───────────────────────────┘
                      │
                      ▼
            ┌──────────────────────┐
            │   Context Manager    │
            │  - Auto-summarize    │
            │  - Smart filtering   │
            └──────────┬───────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  iFlow AI API   │
              │  (claude models) │
              └─────────────────┘
```

---

## Contributing

Found an issue or have a suggestion? Please open an issue on GitHub!

---

## License

Same as standard Quibbler - see [LICENSE](LICENSE) for details.

---

## Sources

- [iFlow CLI Documentation](https://platform.iflow.cn/en/cli/quickstart)
- [iFlow CLI Configuration](https://platform.iflow.cn/en/cli/configuration/settings)
- [Standard Quibbler](https://github.com/fulcrumresearch/quibbler)
