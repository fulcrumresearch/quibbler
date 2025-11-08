import logging
from pathlib import Path

from quibbler.config import get_quibbler_home


LOG_DIR = get_quibbler_home()
LOG_FILE = LOG_DIR / "quibbler.log"


def create_log_dir() -> None:
    """Create log directory idempotently."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Get a logger instance with name `name`."""

    # ensure log directory exists
    create_log_dir()

    # get logger instance
    logger = logging.getLogger(name)

    # if logger already has handlers, return it
    if logger.handlers:
        return logger

    # otherwise, configure logger
    logger.setLevel(level)
    logger.propagate = False  # avoid duplicate logs from parent loggers
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
