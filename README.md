# Quibbler

Quibbler is a code review agent that integrates with AI coding assistants. It actively reviews proposed code changes before they're implemented, catching quality issues, hallucinations, and pattern violations.

Unlike simple linters or static analysis tools, Quibbler is an agent: it can read and understand your codebase context to provide intelligent, context-aware feedback.

## What Quibbler Prevents

We've found Quibbler useful in preventing agents from:

- Fabricating results without running commands
- Not running tests or skipping verification steps
- Not following your coding style and patterns
- Hallucinating numbers, metrics, or functionality
- Creating new patterns instead of following existing ones
- Making changes that don't align with user intent

Quibbler maintains context across reviews, learning your project's patterns and rules over time.

## Installation

Using pip:

```bash
pip install quibbler
```

Using uv:

```bash
uv tool install quibbler
```

## Choosing Your Mode

Quibbler supports two integration modes:

### MCP Mode (Recommended for Most Users)

Best for: **Cursor, Claude Desktop, and other MCP-compatible agents**

- Uses the Model Context Protocol for universal compatibility
- Agent calls `review_code` tool before making changes
- Synchronous review with blocking feedback
- Simple setup via MCP server configuration

### Hook Mode (For Claude Code Power Users)

Best for: **Claude Code users wanting deeper integration**

- Uses Claude Code's hook system for event-driven monitoring
- Passively observes all agent actions (tool use, prompts, etc.)
- Fire-and-forget feedback injection via file writes
- More powerful affordances but Claude Code-specific

## Setup

Choose your mode and follow the appropriate setup instructions:

### Option A: MCP Mode Setup

#### 1. Configure MCP Server

Add Quibbler to your agent's MCP server configuration.

**For Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "quibbler": {
      "command": "quibbler mcp",
      "env": {
        "ANTHROPIC_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

**For Cursor** (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "quibbler": {
      "command": "quibbler mcp",
      "env": {
        "ANTHROPIC_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

**For other MCP-compatible agents**: Refer to your agent's documentation for MCP server configuration.

#### 2. Add to AGENTS.md

Create or update `AGENTS.md` in your project root to instruct your agent to use Quibbler:

```markdown
## Code Review Process

Before writing, editing, or running any code, you MUST call the `review_code` tool from the Quibbler MCP server with:

- `user_instructions`: The exact instructions the user gave you
- `agent_plan`: **The specific code changes you plan to make** (not just a general description - include file names, function signatures, key logic, and implementation details)
- `project_path`: The absolute path to this project

Wait for Quibbler's feedback before proceeding. Only proceed if Quibbler approves or address any concerns raised.

### Example

User asks: "Add authentication to the API"

Before writing code, call:

review_code(
user_instructions="Add authentication to the API",
agent_plan="""I plan to make these specific changes:

1. Create auth/jwt.py with verify_token() and create_token() functions
2. Add JWT middleware to routes/api.py with @require_auth decorator
3. Update User model with password_hash field and verify_password() method
4. Create /auth/login endpoint in routes/auth.py""",
   project_path="/absolute/path/to/project"
   )

Wait for approval before implementing.
```

### Option B: Hook Mode Setup

#### 1. Start Quibbler Hook Server

In a terminal, start the Quibbler hook server:

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
quibbler hook server
# Or specify a custom port:
quibbler hook server 8081
# Or use the shorthand (defaults to 'server' subcommand):
quibbler hook 8081
```

Keep this server running in the background. It will receive hook events from Claude Code.

#### 2. Configure Hooks in Your Project

In your project directory, run:

```bash
quibbler hook add
```

This creates or updates `.claude/settings.json` with the necessary hooks to forward events to the Quibbler server.

#### 3. Verify Setup

The `.claude/settings.json` should now contain hooks that:

- Forward tool use events to Quibbler (`quibbler hook forward`)
- Display Quibbler feedback to the agent (`quibbler hook notify`)

When Claude Code runs in this project, Quibbler will automatically observe and intervene when needed.

## Configuration

By default, Quibbler uses Claude Haiku 4.5 for speed. You can change this by creating or editing:

**Global config** (`~/.quibbler/config.json`):

```json
{
  "model": "claude-sonnet-4-20250514"
}
```

**Project-specific config** (`.quibbler/config.json` in your project):

```json
{
  "model": "claude-sonnet-4-20250514"
}
```

Project-specific config takes precedence over global config.

## How It Works

### MCP Mode

1. Your agent calls the `review_code` tool with user instructions and proposed changes
2. Quibbler maintains a persistent review agent per project that:
   - Reviews the proposed changes against user intent
   - Uses Read tool to check existing patterns in your codebase
   - Validates claims and checks for hallucinations
   - Ensures proper testing and verification steps
3. Quibbler returns feedback or approval synchronously
4. Your agent proceeds only after addressing concerns

### Hook Mode

1. Claude Code triggers hooks on events (tool use, prompt submission, etc.)
2. Hook events are forwarded to the Quibbler HTTP server
3. Quibbler maintains a persistent observer agent per session that:
   - Passively watches all agent actions
   - Builds understanding of what the agent is doing
   - Intervenes when necessary by writing feedback to `.quibbler/{session_id}.txt`
4. Feedback is automatically displayed to the agent via the notify hook
5. The agent sees the feedback and can adjust its behavior

Both modes build understanding over time, learning your project's patterns and saving rules to `.quibbler/rules.md`.

## Customizing Prompts

You can customize Quibbler's system prompt by editing `~/.quibbler/prompt.md`. The default prompt will be created on first run.

Project-specific rules in `.quibbler/rules.md` are automatically loaded and added to the prompt.

**Note for Hook Mode**: Your system prompt should include a `{message_file}` placeholder where you want Quibbler to write feedback. For example:

```markdown
When you need to intervene, write your feedback to {message_file}
```

## Contributing

If you notice an issue or bug, please [open an issue](https://github.com/fulcrumresearch/quibbler/issues). We welcome contributions - feel free to open a PR.

Join our community on [Discord](https://discord.gg/QmMybVuwWp) to discuss workflows and share experiences.

## License

See [LICENSE](LICENSE) for details.
