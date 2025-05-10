from app.db.postgres import Base, engine
from app.utils.vector_store import init_vector_store
from app.core.config import settings

def init_db():
    """
    Initialize database tables and create initial data if needed
    """
    # Create all tables defined in SQLAlchemy models
    Base.metadata.create_all(bind=engine)
    
    # Initialize vector store for document embeddings
    init_vector_store()
    
    print("Database initialized successfully")
    
    # Keep the async version for compatibility or future use
    
async def init_db_async():
    """
    Async version of init_db for compatibility
    """
    # Call the sync version for now
    init_db()