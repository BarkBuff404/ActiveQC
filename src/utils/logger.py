import logging
import os
import sys
from datetime import datetime
from src.config.settings import settings

def setup_logger():
    """
        Sets up logging manually without using basicConfig (Python 3.13+ safe). Returns the full path to the generated log file.
    """
    log_file = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"
    logs_path = settings.LOG_DIR
    os.makedirs(logs_path, exist_ok=True)
    log_file_path = os.path.join(logs_path, log_file)

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Clear existing handlers to prevent duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # File handler
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s'))

    # Console handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))

    # Add both handlers
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return log_file_path

# Initialize logging on import
LOG_FILE_PATH = setup_logger()