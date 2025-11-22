"""
Enhanced logging system with structured output and metrics tracking.

Features:
- Structured JSON logging for machine parsing
- Performance metrics tracking
- Review session analytics
- Separate log files for different purposes
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_DIR = Path.home() / ".quibbler"
MAIN_LOG = LOG_DIR / "quibbler.log"
METRICS_LOG = LOG_DIR / "metrics.jsonl"  # JSON Lines format for easy parsing
REVIEWS_LOG = LOG_DIR / "reviews.jsonl"


def create_log_dir() -> None:
    """Create log directory idempotently"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)


class MetricsLogger:
    """Logger for tracking review metrics and analytics"""

    def __init__(self):
        create_log_dir()
        self.metrics_file = METRICS_LOG
        self.reviews_file = REVIEWS_LOG

    def log_metric(self, metric_name: str, value: Any, tags: dict[str, Any] = None):
        """
        Log a metric with tags.

        Args:
            metric_name: Name of the metric
            value: Metric value
            tags: Additional tags/metadata
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metric": metric_name,
            "value": value,
            "tags": tags or {},
        }

        try:
            with open(self.metrics_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logging.error(f"Failed to log metric: {e}")

    def log_review(
        self,
        session_id: str,
        project_path: str,
        review_type: str,
        user_instructions: str,
        agent_plan: str,
        feedback: str,
        context_size: int,
        has_summary: bool,
    ):
        """
        Log a complete review session.

        Args:
            session_id: Session identifier
            project_path: Project path
            review_type: "mcp" or "hook"
            user_instructions: User's original instructions
            agent_plan: Agent's implementation plan
            feedback: Quibbler's feedback
            context_size: Number of messages in context
            has_summary: Whether context has been summarized
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "project_path": project_path,
            "type": review_type,
            "user_instructions_length": len(user_instructions),
            "agent_plan_length": len(agent_plan),
            "feedback_length": len(feedback),
            "context_size": context_size,
            "has_summary": has_summary,
            "approved": "✅" in feedback or "APPROVED" in feedback,
            "issues_found": "❌" in feedback or "ISSUES" in feedback,
        }

        try:
            with open(self.reviews_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logging.error(f"Failed to log review: {e}")

    def get_session_stats(self, session_id: str = None) -> dict[str, Any]:
        """
        Get statistics for a session or all sessions.

        Args:
            session_id: Optional session ID to filter by

        Returns:
            Dictionary with statistics
        """
        if not self.reviews_file.exists():
            return {
                "total_reviews": 0,
                "approved": 0,
                "issues_found": 0,
                "avg_context_size": 0,
                "summarized_sessions": 0,
            }

        reviews = []
        try:
            with open(self.reviews_file) as f:
                for line in f:
                    review = json.loads(line)
                    if session_id is None or review.get("session_id") == session_id:
                        reviews.append(review)
        except Exception as e:
            logging.error(f"Failed to read reviews: {e}")
            return {}

        if not reviews:
            return {
                "total_reviews": 0,
                "approved": 0,
                "issues_found": 0,
                "avg_context_size": 0,
                "summarized_sessions": 0,
            }

        return {
            "total_reviews": len(reviews),
            "approved": sum(1 for r in reviews if r.get("approved")),
            "issues_found": sum(1 for r in reviews if r.get("issues_found")),
            "avg_context_size": sum(r.get("context_size", 0) for r in reviews)
            / len(reviews),
            "summarized_sessions": sum(1 for r in reviews if r.get("has_summary")),
            "avg_feedback_length": sum(r.get("feedback_length", 0) for r in reviews)
            / len(reviews),
        }


class StructuredLogger(logging.Logger):
    """Logger that supports both traditional and structured logging"""

    def __init__(self, name: str, level: int = logging.INFO):
        super().__init__(name, level)
        self.metrics = MetricsLogger()

    def structured(self, message: str, **kwargs):
        """
        Log a structured message with additional fields.

        Args:
            message: Log message
            **kwargs: Additional structured fields
        """
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "logger": self.name,
            "message": message,
            **kwargs,
        }
        self.info(json.dumps(data))


def get_enhanced_logger(name: str, level: int = logging.INFO) -> StructuredLogger:
    """
    Get an enhanced logger instance with structured logging support.

    Args:
        name: Logger name
        level: Logging level

    Returns:
        StructuredLogger instance
    """
    create_log_dir()

    # Check if logger already exists
    existing = logging.getLogger(name)
    if isinstance(existing, StructuredLogger) and existing.handlers:
        return existing

    # Create new structured logger
    logger = StructuredLogger(name, level)
    logger.propagate = False

    # File handler for main log
    file_handler = logging.FileHandler(MAIN_LOG)
    file_handler.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
