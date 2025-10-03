from sqlalchemy import text
from sqlalchemy.ext.declarative import declarative_base
from app.db.postgres import get_db, engine
import numpy as np
from psycopg2.extensions import register_adapter, AsIs
import json
import time
import uuid
import gc
from typing import List, Dict, Any, Optional, Tuple
import logging
from app.core.config import settings
import threading
import contextlib
from app.utils.rag_cache import cached

# Import for HybridVectorStore class
from app.db.database_service import get_database_service
from app.utils.embeddings import generate_embedding

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


@cached("vsearch", ttl=86400)  # 24 hours
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
    # TODO: Cache similarity search results for query_embedding + limit + threshold + filters
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


# Processing strategy enum values
PROCESSING_STRATEGY_DIRECT = "direct_llm"
PROCESSING_STRATEGY_HYBRID = "hybrid"
PROCESSING_STRATEGY_FULL_RAG = "full_rag"


class HybridVectorStore:
    """
    Enhanced vector store class that supports the hybrid RAG approach
    by providing specialized functions for different document processing strategies.
    """

    def __init__(self, database_service=None):
        """
        Initialize the hybrid vector store.

        Args:
            database_service: Optional database service to use for document operations
        """
        self.db_service = database_service or get_database_service()
        self.initialized = init_vector_store()
        logger.info(f"Hybrid vector store initialized: {self.initialized}")

    def add_embedding(self, document_id: str, chunk_id: str, content: str,
                     embedding: List[float], metadata: Optional[Dict[str, Any]] = None,
                     timeout: int = 30) -> Optional[int]:
        """
        Add an embedding to the vector store with enhanced metadata tracking.

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
        # Ensure metadata is a dictionary
        metadata = metadata or {}

        # Add processing timestamp
        metadata["processed_at"] = time.time()

        # Call the base implementation
        return add_embedding(
            document_id=document_id,
            chunk_id=chunk_id,
            content=content,
            embedding=embedding,
            metadata=metadata,
            timeout=timeout
        )

    def batch_add_embeddings_with_strategy(
        self,
        embeddings_data: List[Dict[str, Any]],
        strategy: str,
        batch_size: int = 10,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        Add multiple embeddings in batches with strategy-specific optimizations.

        Args:
            embeddings_data: List of dictionaries containing embedding data
            strategy: The processing strategy used
            batch_size: Number of embeddings to insert in a single batch
            timeout: Database operation timeout in seconds

        Returns:
            Dictionary with success and error counts
        """
        # Adjust batch size based on strategy
        if strategy == PROCESSING_STRATEGY_HYBRID:
            # For hybrid approach, use smaller batches for faster initial results
            batch_size = min(5, batch_size)
        elif strategy == PROCESSING_STRATEGY_FULL_RAG:
            # For full RAG, use larger batches for efficiency
            batch_size = max(20, batch_size)

        # Log the strategy and batch size
        logger.info(f"Using strategy {strategy} with batch size {batch_size} for {len(embeddings_data)} embeddings")

        # Add strategy to metadata for each embedding
        for item in embeddings_data:
            item["metadata"] = item.get("metadata", {})
            item["metadata"]["strategy"] = strategy

        # Call the base implementation
        return batch_add_embeddings(
            embeddings_data=embeddings_data,
            batch_size=batch_size,
            timeout=timeout
        )

    def similarity_search_with_strategy(
        self,
        query_embedding: List[float],
        strategy: Optional[str] = None,
        limit: int = 5,
        similarity_threshold: float = 0.5,
        filter_dict: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents with strategy-specific filtering.

        Args:
            query_embedding: The embedding to search with
            strategy: Optional strategy to filter results
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score (0-1) to include
            filter_dict: Optional filter criteria based on metadata fields
            timeout: Database operation timeout in seconds

        Returns:
            List of matching document chunks with similarity scores
        """
        # TODO: Cache strategy-specific search results for query_embedding + strategy + filters
        # Initialize filter dictionary if not provided
        filter_dict = filter_dict or {}

        # Add strategy filter if specified
        if strategy:
            filter_dict["strategy"] = strategy

        # Call the base implementation
        return similarity_search(
            query_embedding=query_embedding,
            limit=limit,
            similarity_threshold=similarity_threshold,
            filter_dict=filter_dict,
            timeout=timeout
        )

    def process_document_vectors(
        self,
        document_id: str,
        chunks: List[Dict[str, Any]],
        strategy: str,
        embeddings: Optional[List[List[float]]] = None
    ) -> Dict[str, Any]:
        """
        Process document chunks and add to vector store based on strategy.

        Args:
            document_id: The document ID
            chunks: List of document chunks with content
            strategy: Processing strategy to use
            embeddings: Optional pre-generated embeddings (if available)

        Returns:
            Dictionary with processing results
        """
        start_time = time.time()
        logger.info(f"Processing vectors for document {document_id} with strategy {strategy}")

        results = {
            "document_id": document_id,
            "strategy": strategy,
            "chunks_processed": 0,
            "embeddings_added": 0,
            "errors": 0
        }

        # Handle different strategies
        if strategy == PROCESSING_STRATEGY_DIRECT:
            # For direct LLM, we don't need to add embeddings
            # Just store metadata about the document for later reference
            if chunks and self.db_service:
                for i, chunk in enumerate(chunks):
                    chunk_id = chunk.get("id", f"{document_id}_chunk_{i}")
                    content = chunk.get("content", "")

                    self.db_service.create_document_chunk(
                        document_id=document_id,
                        content=content,
                        chunk_index=i,
                        metadata={"strategy": strategy, "direct_processed": True}
                    )
                    results["chunks_processed"] += 1

            logger.info(f"Document {document_id} processed with DIRECT_LLM strategy (no embeddings)")

        elif strategy == PROCESSING_STRATEGY_HYBRID:
            # For hybrid, process a subset of chunks immediately and schedule the rest
            if not chunks:
                logger.warning(f"No chunks to process for document {document_id}")
                return results

            # Determine how many chunks to process immediately (e.g., first 3)
            immediate_count = min(3, len(chunks))
            immediate_chunks = chunks[:immediate_count]
            deferred_chunks = chunks[immediate_count:]

            # Process immediate chunks
            embeddings_data = []
            for i, chunk in enumerate(immediate_chunks):
                chunk_id = chunk.get("id", f"{document_id}_chunk_{i}")
                content = chunk.get("content", "")

                if not content:
                    continue

                try:
                    # Generate embedding if not provided
                    chunk_embedding = None
                    if embeddings and i < len(embeddings):
                        chunk_embedding = embeddings[i]
                    else:
                        chunk_embedding = generate_embedding(content)

                    # Add embedding data
                    embeddings_data.append({
                        "document_id": document_id,
                        "chunk_id": chunk_id,
                        "content": content,
                        "embedding": chunk_embedding,
                        "metadata": {
                            "strategy": strategy,
                            "chunk_index": i,
                            "priority": "high"
                        }
                    })
                    results["chunks_processed"] += 1
                except Exception as e:
                    logger.error(f"Error preparing chunk {chunk_id}: {str(e)}")
                    results["errors"] += 1

            # Add immediate embeddings to vector store
            if embeddings_data:
                batch_results = self.batch_add_embeddings_with_strategy(
                    embeddings_data=embeddings_data,
                    strategy=strategy,
                    batch_size=5
                )
                results["embeddings_added"] = batch_results.get("success", 0)

            # Schedule deferred chunks for later processing
            for i, chunk in enumerate(deferred_chunks, start=immediate_count):
                content = chunk.get("content", "")
                chunk_id = chunk.get("id", f"{document_id}_chunk_{i}")

                if not content:
                    continue

                self.db_service.create_document_chunk(
                    document_id=document_id,
                    content=content,
                    chunk_index=i,
                    metadata={
                        "strategy": strategy,
                        "deferred": True,
                        "priority": "medium"
                    }
                )
                results["chunks_processed"] += 1

            logger.info(f"Document {document_id} processed with HYBRID strategy: "
                       f"{results['embeddings_added']} immediate embeddings, "
                       f"{len(deferred_chunks)} deferred chunks")

        elif strategy == PROCESSING_STRATEGY_FULL_RAG:
            # For full RAG, process all chunks with embeddings
            if not chunks:
                logger.warning(f"No chunks to process for document {document_id}")
                return results

            # Prepare all chunks for embedding
            embeddings_data = []
            for i, chunk in enumerate(chunks):
                chunk_id = chunk.get("id", f"{document_id}_chunk_{i}")
                content = chunk.get("content", "")

                if not content:
                    continue

                try:
                    # Generate embedding if not provided
                    chunk_embedding = None
                    if embeddings and i < len(embeddings):
                        chunk_embedding = embeddings[i]
                    else:
                        chunk_embedding = generate_embedding(content)

                    # Add embedding data
                    embeddings_data.append({
                        "document_id": document_id,
                        "chunk_id": chunk_id,
                        "content": content,
                        "embedding": chunk_embedding,
                        "metadata": {
                            "strategy": strategy,
                            "chunk_index": i,
                            "priority": "normal"
                        }
                    })
                    results["chunks_processed"] += 1
                except Exception as e:
                    logger.error(f"Error preparing chunk {chunk_id}: {str(e)}")
                    results["errors"] += 1

            # Add all embeddings to vector store
            if embeddings_data:
                batch_results = self.batch_add_embeddings_with_strategy(
                    embeddings_data=embeddings_data,
                    strategy=strategy,
                    batch_size=20
                )
                results["embeddings_added"] = batch_results.get("success", 0)

            logger.info(f"Document {document_id} processed with FULL_RAG strategy: "
                       f"{results['embeddings_added']} embeddings added")

        # Calculate processing time
        processing_time = time.time() - start_time
        results["processing_time"] = round(processing_time, 2)

        # Force garbage collection after processing
        gc.collect()

        return results

    @cached("hsearch", ttl=21600)  # 6 hours
    def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        document_ids: Optional[List[str]] = None,
        limit: int = 5,
        similarity_threshold: float = 0.5,  # Added adaptive threshold parameter
        direct_limit: Optional[int] = None,
        hybrid_limit: Optional[int] = None,
        full_rag_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Perform a hybrid search that combines results from different processing strategies.

        This search prioritizes results based on the processing strategy hierarchy:
        1. DIRECT_LLM - Quick responses from small documents
        2. HYBRID - Balance of speed and quality for medium documents
        3. FULL_RAG - Comprehensive search for large documents

        Args:
            query: The search query text
            query_embedding: The query text embedding
            document_ids: Optional list of specific document IDs to search in
            limit: Total maximum results to return
            similarity_threshold: Adaptive similarity threshold (default 0.5)
            direct_limit: Maximum results from DIRECT_LLM strategy (None for auto)
            hybrid_limit: Maximum results from HYBRID strategy (None for auto)
            full_rag_limit: Maximum results from FULL_RAG strategy (None for auto)

        Returns:
            Dictionary with combined search results and metadata
        """
        # TODO: Cache complete hybrid search results for all search parameters
        start_time = time.time()

        # Auto-calculate limits if not specified
        if direct_limit is None and hybrid_limit is None and full_rag_limit is None:
            # Default distribution: prioritize direct and hybrid results
            direct_limit = limit // 3
            hybrid_limit = limit // 3
            full_rag_limit = limit - direct_limit - hybrid_limit
        else:
            # Ensure specified limits don't exceed total
            direct_limit = direct_limit or 0
            hybrid_limit = hybrid_limit or 0
            full_rag_limit = full_rag_limit or 0

            # Adjust if sum exceeds limit
            if direct_limit + hybrid_limit + full_rag_limit > limit:
                # Scale down proportionally
                total = direct_limit + hybrid_limit + full_rag_limit
                direct_limit = int(direct_limit * limit / total)
                hybrid_limit = int(hybrid_limit * limit / total)
                full_rag_limit = limit - direct_limit - hybrid_limit

        # Initialize results
        results = {
            "query": query,
            "total_results": 0,
            "results": [],
            "strategy_counts": {
                "direct_llm": 0,
                "hybrid": 0,
                "full_rag": 0
            },
            "timing": {}
        }

        # Create filter for document IDs if specified
        filter_dict = {}
        if document_ids:
            filter_dict["document_ids"] = document_ids

        # Search using each strategy with appropriate limit and adaptive threshold
        if direct_limit > 0:
            with timed_operation("direct_llm_search"):
                direct_results = self.similarity_search_with_strategy(
                    query_embedding=query_embedding,
                    strategy=PROCESSING_STRATEGY_DIRECT,
                    limit=direct_limit,
                    similarity_threshold=similarity_threshold,  # Pass adaptive threshold
                    filter_dict=filter_dict
                )
                results["strategy_counts"]["direct_llm"] = len(direct_results)
                results["results"].extend(direct_results)

        if hybrid_limit > 0:
            with timed_operation("hybrid_search"):
                hybrid_results = self.similarity_search_with_strategy(
                    query_embedding=query_embedding,
                    strategy=PROCESSING_STRATEGY_HYBRID,
                    limit=hybrid_limit,
                    similarity_threshold=similarity_threshold,  # Pass adaptive threshold
                    filter_dict=filter_dict
                )
                results["strategy_counts"]["hybrid"] = len(hybrid_results)
                results["results"].extend(hybrid_results)

        if full_rag_limit > 0:
            with timed_operation("full_rag_search"):
                full_rag_results = self.similarity_search_with_strategy(
                    query_embedding=query_embedding,
                    strategy=PROCESSING_STRATEGY_FULL_RAG,
                    limit=full_rag_limit,
                    similarity_threshold=similarity_threshold,  # Pass adaptive threshold
                    filter_dict=filter_dict
                )
                results["strategy_counts"]["full_rag"] = len(full_rag_results)
                results["results"].extend(full_rag_results)

        # Sort combined results by similarity score
        results["results"].sort(key=lambda x: x.get("similarity", 0), reverse=True)

        # Limit to requested total if needed
        if len(results["results"]) > limit:
            results["results"] = results["results"][:limit]

        results["total_results"] = len(results["results"])
        results["timing"]["total_seconds"] = round(time.time() - start_time, 2)

        return results


# Singleton instance
_hybrid_vector_store = None


def get_hybrid_vector_store(db_service=None):
    """
    Get or create the singleton hybrid vector store instance.

    Args:
        db_service: Optional database service to use

    Returns:
        HybridVectorStore instance
    """
    global _hybrid_vector_store
    if _hybrid_vector_store is None:
        _hybrid_vector_store = HybridVectorStore(db_service)
    return _hybrid_vector_store