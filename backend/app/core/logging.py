"""One place that sets up logging for the whole backend.

Every module just does `logger = logging.getLogger(__name__)`; this
function decides where those messages go and how they look. Full
tracebacks are logged here (never returned to API clients), so this is
where you look when something fails.
"""

import logging

from app.core import config

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def configure_logging() -> None:
    """Safe to call more than once: basicConfig does nothing if the root
    logger already has handlers (e.g. under pytest or after a reload)."""
    logging.basicConfig(level=config.LOG_LEVEL, format=LOG_FORMAT)
