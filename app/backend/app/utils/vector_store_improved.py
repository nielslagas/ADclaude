from sqlalchemy import text
from sqlalchemy.ext.declarative import declarative_base
from app.db.postgres import get_db, engine
import numpy as np
from psycopg2.extensions import register_adapter, AsIs
import json
import time
import uuid
from typing import List, Dict, Any, Optional
import logging
from app.core.config import settings
import threading
import contextlib

# Custom JSON encoder for UUIDs
class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return super().default(obj)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Thread lock for database operations
db_lock = threading.Lock()

def adapt_numpy_array(numpy_array):
    """
    Convert numpy array to a format suitable for PostgreSQL pgvector
    """
    return AsIs(repr(numpy_array.tolist()))


def create_vector_extension():
    """
    Create the pgvector extension in the database if it doesn't exist
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
        logger.info("Vector extension created successfully")
    except Exception as e:
        logger.error(f"Error creating vector extension: {str(e)}")
        raise


def create_embeddings_table(dimension: int = 768):
    """
    Create a table for document embeddings if it doesn't exist
    
    Args:
        dimension: The dimension of the embedding vectors (default 768)
    """
    try:
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS document_embeddings (
            id SERIAL PRIMARY KEY,
            document_id UUID NOT NULL,
            chunk_id TEXT NOT NULL,
            content TEXT NOT NULL,
            embedding vector({dimension}),
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(document_id, chunk_id)
        );
        """
        
        create_index_sql = """
        CREATE INDEX IF NOT EXISTS document_embeddings_document_id_idx ON document_embeddings (document_id);
        """
        
        with engine.connect() as conn:
            conn.execute(text(create_table_sql))
            conn.execute(text(create_index_sql))
            conn.commit()
        logger.info(f"Embeddings table created with dimension {dimension}")
    except Exception as e:
        logger.error(f"Error creating embeddings table: {str(e)}")
        raise


def add_embedding(
    document_id: str,
    chunk_id: str,
    content: str,
    embedding: List[float],
    metadata: Optional[Dict[str, Any]] = None,
    timeout: int = 30
) -> Optional[int]:
    """
    Add an embedding to the document_embeddings table with improved error handling and timeouts
    
    Args:
        document_id: UUID of the document
        chunk_id: ID for the specific chunk
        content: Text content of the chunk
        embedding: Vector embedding of the chunk content
        metadata: Additional metadata for the chunk
        timeout: Database operation timeout in seconds
        
    Returns:
        ID of the embedding record or None if operation failed
    """
    # Convert metadata to JSON string using UUIDEncoder for UUID objects
    metadata_str = json.dumps(metadata, cls=UUIDEncoder) if metadata else "{}"
    
    # Use a more direct SQL approach with formatted SQL
    insert_sql = """
    INSERT INTO document_embeddings (document_id, chunk_id, content, embedding, metadata)
    VALUES (%s, %s, %s, %s, %s::jsonb)
    ON CONFLICT (document_id, chunk_id) 
    DO UPDATE SET
        content = EXCLUDED.content,
        embedding = EXCLUDED.embedding,
        metadata = EXCLUDED.metadata
    RETURNING id;
    """
    
    start_time = time.time()
    
    try:
        # Use a lock to prevent concurrent access issues
        with db_lock:
            # Create direct connection to execute raw SQL
            from app.db.postgres import get_raw_connection
            conn = get_raw_connection()
            
            try:
                # Set statement timeout
                with conn.cursor() as timeout_cursor:
                    timeout_cursor.execute(f"SET statement_timeout = {timeout * 1000};")
                
                # Execute the insert
                with conn.cursor() as cursor:
                    logger.debug(f"Inserting embedding for chunk_id: {chunk_id}")
                    cursor.execute(insert_sql, (document_id, chunk_id, content, embedding, metadata_str))
                    row = cursor.fetchone()
                    conn.commit()
                    
                    if row and row[0]:
                        logger.info(f"Successfully added embedding for chunk_id: {chunk_id} in {time.time() - start_time:.2f}s")
                        return row[0]
                    else:
                        logger.error(f"Failed to add embedding, no row returned")
                        return None
            except Exception as db_error:
                logger.error(f"Database error while adding embedding: {str(db_error)}")
                conn.rollback()
                return None
            finally:
                conn.close()
    except Exception as e:
        logger.error(f"Error adding embedding to vector store: {str(e)}")
        return None


def similarity_search(
    query_embedding: List[float], 
    limit: int = 5, 
    similarity_threshold: float = 0.5,
    filter_dict: Optional[Dict[str, Any]] = None,
    timeout: int = 30
) -> List[Dict[str, Any]]:
    """
    Search for similar documents based on embedding similarity with improved error handling
    
    Args:
        query_embedding: The embedding to search with
        limit: Maximum number of results to return (default 5)
        similarity_threshold: Minimum similarity score (0-1) to include in results (default 0.5)
        filter_dict: Optional filter criteria based on metadata fields
        timeout: Database operation timeout in seconds
        
    Returns:
        List of matching document chunks with similarity scores
    """
    # Build WHERE conditions
    conditions = []
    params = {
        "query_embedding": query_embedding, 
        "limit": limit,
        "similarity_threshold": similarity_threshold
    }
    
    # Add threshold condition
    threshold_condition = "(1 - (embedding <=> :query_embedding)) >= :similarity_threshold"
    conditions.append(threshold_condition)
    
    # Add metadata filters if provided
    if filter_dict:
        for i, (key, value) in enumerate(filter_dict.items()):
            filter_key = f"filter_{i}"
            conditions.append(f"metadata->>{key!r} = :{filter_key}")
            params[filter_key] = value
    
    # Combine all conditions
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    
    search_sql = f"""
    SELECT 
        id,
        document_id,
        chunk_id,
        content,
        metadata,
        1 - (embedding <=> :query_embedding) as similarity
    FROM document_embeddings
    {where_clause}
    ORDER BY embedding <=> :query_embedding
    LIMIT :limit;
    """
    
    try:
        # Set statement timeout
        with engine.connect() as conn:
            conn.execute(text(f"SET statement_timeout = {timeout * 1000};"))
            conn.commit()
        
        # Execute search
        with engine.connect() as conn:
            result = conn.execute(text(search_sql), params)
            results = result.fetchall()
            logger.info(f"Similarity search found {len(results)} results above threshold {similarity_threshold}")
            return [dict(row._mapping) for row in results]
    except Exception as e:
        logger.error(f"Error in similarity search: {str(e)}")
        return []


@contextlib.contextmanager
def timed_operation(name: str):
    """Context manager for timing database operations"""
    start_time = time.time()
    logger.info(f"Starting {name}...")
    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.info(f"Completed {name} in {duration:.2f}s")


# Initialize vector store
def init_vector_store(dimension: int = None):
    """
    Initialize the vector store by creating necessary extensions and tables
    
    Args:
        dimension: Optional specific embedding dimension to use (default: use config value)
    """
    try:
        with timed_operation("vector store initialization"):
            # Use dimension from settings or parameter
            embed_dimension = dimension or settings.EMBEDDING_DIMENSION
            
            # Register numpy array adapter for pgvector
            register_adapter(np.ndarray, adapt_numpy_array)
            
            # Create pgvector extension
            with timed_operation("creating vector extension"):
                create_vector_extension()
            
            # Create tables for embeddings
            with timed_operation("creating embeddings table"):
                create_embeddings_table(embed_dimension)
            
            logger.info(f"Vector store initialized successfully with {embed_dimension} dimensions")
            return True
    except Exception as e:
        logger.error(f"Error initializing vector store: {e}")
        return False


def batch_add_embeddings(
    embeddings_data: List[Dict[str, Any]],
    batch_size: int = 10,
    timeout: int = 60
) -> Dict[str, Any]:
    """
    Efficiently add multiple embeddings in batches
    
    Args:
        embeddings_data: List of dictionaries containing embedding data with keys:
                         document_id, chunk_id, content, embedding, metadata
        batch_size: Number of embeddings to insert in a single batch
        timeout: Database operation timeout in seconds
        
    Returns:
        Dictionary with success and error counts
    """
    results = {"success": 0, "errors": 0, "failed_chunks": []}
    
    logger.info(f"Adding {len(embeddings_data)} embeddings in batches of {batch_size}")
    
    # Process in batches to avoid memory issues
    for i in range(0, len(embeddings_data), batch_size):
        batch = embeddings_data[i:i+batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}/{(len(embeddings_data)-1)//batch_size + 1} with {len(batch)} embeddings")
        
        # Prepare batch insert
        insert_values = []
        for item in batch:
            metadata_str = json.dumps(item.get("metadata", {}), cls=UUIDEncoder)
            insert_values.append((
                item["document_id"],
                item["chunk_id"],
                item["content"],
                item["embedding"],
                metadata_str
            ))
        
        try:
            # Acquire lock for database operation
            with db_lock:
                from app.db.postgres import get_raw_connection
                conn = get_raw_connection()
                
                try:
                    # Set statement timeout
                    with conn.cursor() as timeout_cursor:
                        timeout_cursor.execute(f"SET statement_timeout = {timeout * 1000};")
                    
                    with conn.cursor() as cursor:
                        # Manually construct batch insert for efficiency
                        args_str = ",".join(cursor.mogrify("(%s,%s,%s,%s,%s::jsonb)", x).decode('utf-8') for x in insert_values)
                        insert_query = f"""
                        INSERT INTO document_embeddings (document_id, chunk_id, content, embedding, metadata)
                        VALUES {args_str}
                        ON CONFLICT (document_id, chunk_id) 
                        DO UPDATE SET
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata
                        RETURNING id;
                        """
                        
                        cursor.execute(insert_query)
                        ids = cursor.fetchall()
                        conn.commit()
                        
                        results["success"] += len(ids)
                        logger.info(f"Successfully inserted batch of {len(ids)} embeddings")
                except Exception as db_error:
                    conn.rollback()
                    logger.error(f"Error in batch insert: {str(db_error)}")
                    results["errors"] += len(batch)
                    # Record failed chunk IDs
                    for item in batch:
                        results["failed_chunks"].append(item["chunk_id"])
                finally:
                    conn.close()
        except Exception as e:
            logger.error(f"Error processing batch: {str(e)}")
            results["errors"] += len(batch)
            # Record failed chunk IDs
            for item in batch:
                results["failed_chunks"].append(item["chunk_id"])
    
    return results