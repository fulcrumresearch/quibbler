# Local Installation Guide

This guide shows how to install and use `quibbler-flow` locally without publishing to PyPI.

## Quick Setup

### 1. Clone the Repository

```bash
git clone https://github.com/linroger/quibbler-flow.git
cd quibbler-flow
git checkout claude/quibbler-iflow-cli-01LNU37mzAPUiAP7kqKHiWeq
```

### 2. Install Locally

**Option A: Using uv (recommended)**

```bash
# Install as a tool (isolated)
uv tool install .

# Verify
quibbler --help
quibbler iflow --help
```

**Option B: Using pip**

```bash
# Install globally
pip install .

# Verify
quibbler --help
quibbler iflow --help
```

**Option C: Development mode (editable install)**

```bash
# Install in editable mode with uv
uv pip install -e .

# Or with pip
pip install -e .

# Changes to code will be reflected immediately
quibbler iflow --help
```

### 3. Using without Installation

```bash
# Just sync dependencies and use from virtual environment
uv sync

# Run directly from venv
.venv/bin/quibbler iflow --help
.venv/bin/quibbler iflow mcp
.venv/bin/quibbler iflow hook server
```

## Usage with iFlow CLI

### For MCP Mode

Add to `~/.iflow/mcp.json`:

```json
{
  "mcpServers": {
    "quibbler": {
      "command": "quibbler iflow mcp"
    }
  }
}
```

Or if using from venv without installation:

```json
{
  "mcpServers": {
    "quibbler": {
      "command": "/path/to/quibbler-flow/.venv/bin/quibbler iflow mcp"
    }
  }
}
```

### For Hook Mode

```bash
# Start server
quibbler iflow hook server

# Or from venv
.venv/bin/quibbler iflow hook server

# In another terminal, configure hooks in your project
cd /path/to/your/project
quibbler iflow hook add
```

## Development Workflow

### 1. Make Changes

Edit files in the `quibbler/` directory.

### 2. Test Changes

If using editable install:
```bash
# Changes are immediately available
quibbler iflow --help
```

If using regular install:
```bash
# Reinstall after changes
uv tool install --force .
# Or
pip install --force-reinstall .
```

If using venv directly:
```bash
# Just run from venv
.venv/bin/quibbler iflow --help
```

### 3. Run Tests

```bash
# Activate venv
source .venv/bin/activate

# Test imports
python -c "from quibbler.iflow_client import IFlowClient; print('✓ Imports work')"

# Test CLI
quibbler iflow --help
```

## Troubleshooting

### "quibbler: command not found"

If installed with `uv tool install .`, make sure uv's tool bin is in PATH:

```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"
```

Or use the full path:
```bash
~/.local/bin/quibbler iflow --help
```

### Package name confusion

The package is named `quibbler-flow` in `pyproject.toml` but the CLI command is still `quibbler` and the Python package is still `quibbler/`.

This means:
- Install with: `uv tool install .` (uses name `quibbler-flow`)
- Import with: `from quibbler.iflow_client import ...`
- Run with: `quibbler iflow --help`

### Reinstalling after changes

```bash
# With uv tool
uv tool uninstall quibbler-flow
uv tool install .

# With pip
pip uninstall quibbler-flow
pip install .
```

## Uninstallation

```bash
# If installed with uv tool
uv tool uninstall quibbler-flow

# If installed with pip
pip uninstall quibbler-flow
```

## Distribution

To distribute to others:

### Option 1: GitHub installation

```bash
uv tool install git+https://github.com/linroger/quibbler-flow.git@claude/quibbler-iflow-cli-01LNU37mzAPUiAP7kqKHiWeq
```

### Option 2: Build a wheel

```bash
# Build
uv build

# Distribute the wheel
# dist/quibbler_flow-0.4.0-py3-none-any.whl

# Others can install with:
pip install /path/to/quibbler_flow-0.4.0-py3-none-any.whl
```

### Option 3: Publish to PyPI (future)

```bash
# Build
uv build

# Publish (requires PyPI account)
uv publish
```

## File Structure

```
quibbler-flow/
├── quibbler/              # Python package (import as 'quibbler')
│   ├── __init__.py
│   ├── cli.py            # Entry point (command: 'quibbler')
│   ├── iflow_client.py
│   ├── iflow_agent.py
│   └── ...
├── pyproject.toml        # Package metadata (name: 'quibbler-flow')
├── README.md
├── IFLOW_README.md
└── INSTALL.md           # This file
```

**Key points:**
- **Distribution name:** `quibbler-flow` (in pyproject.toml)
- **Python package:** `quibbler/` (import name)
- **CLI command:** `quibbler` (defined in project.scripts)
