# Quibbler

Quibbler is a code review agent that integrates with AI coding assistants via MCP (Model Context Protocol). It actively reviews proposed code changes before they're implemented, catching quality issues, hallucinations, and pattern violations.

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

## Setup

### 1. Configure MCP Server

Add Quibbler to your agent's MCP server configuration.

**For Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "quibbler": {
      "command": "quibbler",
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
      "command": "quibbler",
      "env": {
        "ANTHROPIC_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

**For other MCP-compatible agents**: Refer to your agent's documentation for MCP server configuration.

### 2. Add to AGENTS.md

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
```

review_code(
user_instructions="Add authentication to the API",
agent_plan="""I plan to make these specific changes:

1. Create auth/jwt.py with:

   - verify_token(token: str) -> User function
   - create_token(user_id: str) -> str function

2. Add JWT middleware to routes/api.py:

   - Import verify_token from auth.jwt
   - Add @require_auth decorator
   - Apply to all /api/\* routes

3. Update User model in models.py:

   - Add password_hash: str field
   - Add verify_password(password: str) -> bool method

4. Create /auth/login endpoint in routes/auth.py:
   - Accept username/password
   - Verify credentials
   - Return JWT token""",
     project_path="/absolute/path/to/project"
     )

```

Wait for approval before implementing.
```

## Configuration

By default, Quibbler uses Claude Haiku 4.5 for speed. You can change this by creating or editing `~/.quibbler/config.json`:

```json
{
  "model": "claude-sonnet-4-20250514"
}
```

## How It Works

1. Your agent calls `review_code` with user instructions and proposed changes
2. Quibbler maintains a persistent agent per project that:
   - Reviews the proposed changes against user intent
   - Uses Read tool to check existing patterns in your codebase
   - Validates claims and checks for hallucinations
   - Ensures proper testing and verification steps
3. Quibbler returns feedback or approval
4. Your agent proceeds only after addressing concerns

Quibbler builds understanding over time, learning your project's patterns and saving rules to `.quibbler/rules.md`.

## Customizing Prompts

You can customize Quibbler's system prompt by editing `~/.quibbler/prompt.md`. The default prompt will be created on first run.

Project-specific rules in `.quibbler/rules.md` are automatically loaded and added to the prompt.

## Contributing

If you notice an issue or bug, please [open an issue](https://github.com/fulcrumresearch/quibbler/issues). We welcome contributions - feel free to open a PR.

Join our community on [Discord](https://discord.gg/QmMybVuwWp) to discuss workflows and share experiences.

## License

See [LICENSE](LICENSE) for details.
