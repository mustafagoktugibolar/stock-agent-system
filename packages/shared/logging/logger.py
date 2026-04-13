import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


_LOG_DIR = Path(__file__).parent.parent.parent.parent / "logs"
_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for the given name.

    Logs go to stdout and, in non-development environments, to a rotating
    file under logs/<name>.log (daily rotation, 7-day retention).
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    from packages.shared.config.settings import get_settings
    settings = get_settings()

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT)

    # Always stream to stdout
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # File handler in non-dev environments
    if settings.app_env != "development":
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = TimedRotatingFileHandler(
            filename=_LOG_DIR / f"{name.replace('.', '_')}.log",
            when="midnight",
            backupCount=7,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger
