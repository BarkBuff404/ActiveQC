from sqlalchemy import create_engine # type: ignore
from src.config.settings import settings
from src.utils.logger import logging

"""
    Establishes a connection to the database.
    Returns:
        Connection object to interact with the database.
    Raises:
        Exception: If the connection fails, an exception is raised with the error details.
"""

def get_db_connection():
    try:
        engine = create_engine(settings.DB_CONNECTION_STRING)
        return engine.connect()
    except Exception as e:
        logging.error(f"Error establishing database connection: {e}")
        raise

def close_db_connection(connection):
    if connection:
        connection.close()
        logging.info("Database connection closed.")
    else:
        logging.warning("No database connection to close.")
