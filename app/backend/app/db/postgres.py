from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import psycopg2
import logging

# Setup logging
logger = logging.getLogger(__name__)

engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Dependency function to get a database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
def get_raw_connection():
    """
    Get a raw psycopg2 connection for direct SQL execution
    """
    try:
        conn = psycopg2.connect(
            host=settings.POSTGRES_SERVER,
            port=settings.POSTGRES_PORT,
            dbname=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        raise