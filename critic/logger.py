import logging
from pathlib import Path
from datetime import datetime

# Create ~/.orchestra directory if it doesn't exist
LOG_DIR = Path.home() / ".critic"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "critic.log"


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with proper configuration"""
    logger = logging.getLogger(name)

    if not logger.handlers:  # Avoid adding duplicate handlers
        logger.setLevel(logging.DEBUG)

        # File handler
        file_handler = logging.FileHandler(LOG_FILE)
        file_handler.setLevel(logging.DEBUG)

        # Format
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    return logger


logger = get_logger(__name__)
logger.info(f"Logging initialized at {datetime.now()}")
