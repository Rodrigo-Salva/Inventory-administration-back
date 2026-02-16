import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger


def setup_logging(log_level: str = "INFO", environment: str = "development"):
    """
    Configura el sistema de logging con formato estructurado
    
    Args:
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        environment: Ambiente de ejecución (development, staging, production)
    """
    
    # Crear directorio de logs si no existe
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configurar formato JSON para logs estructurados
    log_format = "%(asctime)s %(name)s %(levelname)s %(message)s"
    json_formatter = jsonlogger.JsonFormatter(log_format)
    
    # Handler para archivo con rotación
    file_handler = RotatingFileHandler(
        log_dir / "inventory.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(json_formatter)
    
    # Handler para consola (formato legible en desarrollo)
    console_handler = logging.StreamHandler(sys.stdout)
    
    if environment == "development":
        # Formato simple para desarrollo
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
    else:
        # JSON en producción
        console_handler.setFormatter(json_formatter)
    
    # Configurar logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Reducir verbosidad de librerías externas
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger con el nombre especificado
    
    Args:
        name: Nombre del logger (generalmente __name__)
    
    Returns:
        Logger configurado
    """
    return logging.getLogger(name)
