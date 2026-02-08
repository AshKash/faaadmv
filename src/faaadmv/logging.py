"""Logging configuration for faaadmv."""

import logging
from pathlib import Path

import platformdirs


def setup_logging() -> None:
    """Configure logging with file handler for debug output.

    Logs go to ~/.config/faaadmv/debug.log.
    Console output is handled separately by Rich — this is for debug file logging only.
    """
    log_dir = Path(platformdirs.user_config_dir("faaadmv", ensure_exists=True))
    log_file = log_dir / "debug.log"

    # Root logger for the faaadmv namespace
    logger = logging.getLogger("faaadmv")
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers on repeated calls
    if logger.handlers:
        return

    # File handler — detailed debug logging
    try:
        fh = logging.FileHandler(log_file, encoding="utf-8")
    except OSError:
        # If we can't write to the default log dir (common in sandboxed tests),
        # skip file logging rather than crashing the CLI.
        logger.addHandler(logging.NullHandler())
        return
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(fh)

    logger.debug("Logging initialized → %s", log_file)
