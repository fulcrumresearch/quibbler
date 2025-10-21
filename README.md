# Quibbler


`quibbler` is a background agent that monitors your claude code and interrupts it with feedback when it is acting poorly. 

It can help you automatically squash behaviors like:

- not actually running tests, lying about things
- not following previously defined user instructions
- custom defined rules, like using gnarly try/except blocks, not using uv, doing weird imagined backwards compatibility work.


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

Default port is 8081.

You need to configure the claude code hook for quibbler.

Run `quibbler add` to do this, either from a specific project dir you want to add it to, or from `$HOME` if you want it globally.

Then just start claude code! It will run in the background and interrupt your agent when needed.

## License

MIT
