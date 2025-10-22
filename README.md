# Quibbler


Quibbler is a background agent that monitors and critiques your coding agent’s actions using hooks. Unlike most critics and guardrails, Quibbler is an agent: it can read and understand the context of an agent’s action to see if it made a mistake.

We’ve found Quibbler useful in preventing agents from

- fabricating results without running commands
- not running tests
- not following your coding style

In longer running tasks, we found Quibbler useful in enforcing intent, allowing us to check in on our agent less. You can configure your guardrails, and Quibbler learns from your usage. Quibbler currently supports Claude Code: we are adding support for other agents soon!

## Installation

pip:

```bash
pip install quibbler
```

uv:

```bash
uv tool install quibbler
```

## Usage

Start the quibbler server in the background

```bash
quibbler server
```

You then need to configure the claude code hook to send events to quibbler. Run `quibbler add` to do this, either from a specific project dir you want to add it to, or from `$HOME` if you want it globally.

Then just start claude code! Start coding and it will run in the background and interrupt your agent when needed.

## Configuration

By default, quibbler uses Claude Haiku 4.5 for speed - you can change this by creating or editing `~/.quibbler/config.json`:

```json
{
  "model": {anthropic model name}
}
```

## Contributing
.
If you notice an issue or bug, please [open an issue](https://github.com/fulcrumresearch/quibbler/issues). We also welcome contributions: feel free to open a PR to fix an issue.

You can join the user community to discuss issues and workflows you find useful, on [discord](https://discord.gg/QmMybVuwWp).
