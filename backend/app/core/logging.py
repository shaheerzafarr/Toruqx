import logging
import sys
import structlog
from app.core.config import settings

def setup_logging():
    # Set standard library logging level
    log_level = logging.getLevelName(settings.LOG_LEVEL.upper())
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Disable default uvicorn log formatting to avoid double logging / mixing formatters
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        log = logging.getLogger(name)
        log.handlers = []
        log.propagate = True

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if settings.ENV == "development":
        # Human-readable color console rendering
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        # Structured JSON rendering for production/logging collectors
        processors.append(structlog.processors.dict_tracebacks)
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
