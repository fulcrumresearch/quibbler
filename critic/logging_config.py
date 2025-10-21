"""Logging configuration for Critic"""

import logging
from pathlib import Path


def setup_logging():
    """Configure logging to write to ~/.critic/log.txt"""
    log_dir = Path.home() / ".critic"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "log.txt"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)-8s | %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
