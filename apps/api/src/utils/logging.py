import logging
import sys


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure application logging."""
    logger = logging.getLogger("flame-fitness")
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger


logger = setup_logging()
