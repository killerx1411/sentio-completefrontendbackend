import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from config import get_config

logger = logging.getLogger(__name__)
config = get_config()

def get_db_connection():
    """
    Creates and returns a new database connection.
    Uses RealDictCursor to return results as dictionaries.
    """
    try:
         
        conn = psycopg2.connect(
            config.DATABASE_URL,
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to the database: {e}")
        raise e

def init_db():
    """
    Tests the database connection on application startup.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT 1;')
        cur.close()
        conn.close()
        logger.info("Database connection established successfully.")
    except Exception as e:
        logger.error(f"Failed to establish database connection on startup: {e}")
