"""Configuration utilities for Quibbler"""

import os
from pathlib import Path


def get_quibbler_home() -> Path:
    """
    Get the Quibbler home directory.

    Can be customized via QUIBBLER_HOME environment variable.
    Defaults to ~/.quibbler
    """
    home = os.environ.get("QUIBBLER_HOME")
    if home:
        return Path(home).expanduser().resolve()
    return Path.home() / ".quibbler"
