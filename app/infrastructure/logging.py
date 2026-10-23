import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from pythonjsonlogger import jsonlogger


def setup_logging(log_level: str = "INFO", environment: str = "development"):
    """Configura logging estructurado para el proceso."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    formatter = jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    file_handler = RotatingFileHandler(log_dir / "inventory.log", maxBytes=10 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s") if environment == "development" else formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    return root_logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
