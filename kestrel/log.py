"""A small rotating log in %APPDATA%\\Kestrel, so bug reports come with details."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from kestrel import __version__
from kestrel.config import CONFIG_DIR

LOG_FILE = CONFIG_DIR / "kestrel.log"
logger = logging.getLogger("kestrel")


def setup() -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(LOG_FILE, maxBytes=512_000, backupCount=2, encoding="utf-8")
    except OSError:
        return
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info("Kestrel %s starting (Python %s)", __version__, sys.version.split()[0])

    def log_uncaught(kind, error, trace) -> None:
        logger.critical("Uncaught error", exc_info=(kind, error, trace))
        sys.__excepthook__(kind, error, trace)

    sys.excepthook = log_uncaught
