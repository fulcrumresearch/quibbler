# Quibbler


`quibbler` is a background agent that monitors your claude code and interrupts it with feedback when it is acting poorly. 

It can help you automatically squash behaviors like:

- not actually running tests, lying about things
- not following previously defined user instructions
- custom defined rules, like using gnarly try/except blocks, not using uv, doing weird imagined backwards compatibility work.

It will also automatically detect patterns in your refusal and save them as rules for its own monitoring. 

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

### Model Selection

By default, quibbler uses Claude Haiku 4.5 for speed - you can change this by creating or editing `~/.quibbler/config.json`:

```json
{
  "model": "claude-3-5-sonnet-20241022"
}
```
