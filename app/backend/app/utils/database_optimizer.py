"""
Database Query Optimizer for RAG Pipeline
Optimizes PostgreSQL queries, connection pooling, and indexing strategies for better performance
"""

import asyncio
import logging
import time
import threading
from typing import Dict, List, Any, Optional, Tuple
from contextlib import asynccontextmanager
from dataclasses import dataclass
from collections import defaultdict

from sqlalchemy import text, create_engine, pool, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Query performance metrics"""
    query_count: int = 0
    total_execution_time: float = 0.0
    avg_execution_time: float = 0.0
    slow_queries: int = 0  # queries > 1 second
    failed_queries: int = 0
    cache_hits: int = 0


@dataclass
class ConnectionPoolMetrics:
    """Connection pool metrics"""
    active_connections: int = 0
    idle_connections: int = 0
    total_connections: int = 0
    connection_errors: int = 0
    pool_exhaustion_count: int = 0


class QueryCache:
    """Simple query result cache with TTL"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache = {}
        self._timestamps = {}
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired"""
        if key not in self._timestamps:
            return True
        return time.time() - self._timestamps[key] > self.ttl_seconds
    
    def _evict_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self._timestamps.items()
            if current_time - timestamp > self.ttl_seconds
        ]
        
        for key in expired_keys:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)
    
    def _enforce_size_limit(self):
        """Enforce cache size limit using LRU"""
        if len(self._cache) > self.max_size:
            # Sort by timestamp and remove oldest entries
            sorted_items = sorted(self._timestamps.items(), key=lambda x: x[1])
            excess = len(self._cache) - self.max_size
            
            for key, _ in sorted_items[:excess]:
                self._cache.pop(key, None)
                self._timestamps.pop(key, None)
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached result"""
        with self._lock:
            if key in self._cache and not self._is_expired(key):
                self._hits += 1
                return self._cache[key]
            
            self._misses += 1
            return None
    
    def set(self, key: str, value: Any) -> None:
        """Cache a result"""
        with self._lock:
            self._evict_expired()
            self._cache[key] = value
            self._timestamps[key] = time.time()
            self._enforce_size_limit()
    
    def clear(self) -> None:
        """Clear all cached results"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._hits + self._misses
        return {
            'size': len(self._cache),
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': self._hits / max(total_requests, 1),
            'max_size': self.max_size
        }


class OptimizedConnectionPool:
    """Optimized PostgreSQL connection pool"""
    
    def __init__(self, min_connections: int = 5, max_connections: int = 20):
        self.min_connections = min_connections
        self.max_connections = max_connections
        
        # Create connection pool
        self.pool = ThreadedConnectionPool(
            minconn=min_connections,
            maxconn=max_connections,
            host=settings.POSTGRES_SERVER,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            port=settings.POSTGRES_PORT,
            cursor_factory=RealDictCursor
        )
        
        self.metrics = ConnectionPoolMetrics()
        self._lock = threading.Lock()
        
        logger.info(f"Initialized connection pool: {min_connections}-{max_connections} connections")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get connection from pool"""
        connection = None
        try:
            with self._lock:
                try:
                    connection = self.pool.getconn()
                    self.metrics.active_connections += 1
                except Exception as e:
                    self.metrics.connection_errors += 1
                    if "pool exhausted" in str(e).lower():
                        self.metrics.pool_exhaustion_count += 1
                    raise
            
            # Set connection parameters for optimization
            with connection.cursor() as cursor:
                # Optimize for read operations
                cursor.execute("SET default_transaction_isolation = 'read committed'")
                cursor.execute("SET statement_timeout = '30s'")
                cursor.execute("SET lock_timeout = '10s'")
                connection.commit()
            
            yield connection
            
        except Exception as e:
            if connection:
                connection.rollback()
            raise
        finally:
            if connection:
                with self._lock:
                    self.pool.putconn(connection)
                    self.metrics.active_connections -= 1
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get pool status information"""
        return {
            'active_connections': self.metrics.active_connections,
            'min_connections': self.min_connections,
            'max_connections': self.max_connections,
            'connection_errors': self.metrics.connection_errors,
            'pool_exhaustion_count': self.metrics.pool_exhaustion_count
        }
    
    def close(self):
        """Close all connections in pool"""
        if self.pool:
            self.pool.closeall()


class DatabaseOptimizer:
    """Main database optimizer class"""
    
    def __init__(self):
        self.connection_pool = OptimizedConnectionPool()
        self.query_cache = QueryCache()
        self.query_metrics = defaultdict(QueryMetrics)
        
        # Optimized queries for common operations
        self.optimized_queries = self._initialize_optimized_queries()
        
        logger.info("Database optimizer initialized")
    
    def _initialize_optimized_queries(self) -> Dict[str, str]:
        """Initialize optimized SQL queries"""
        return {
            'vector_similarity_search': """
                SELECT 
                    id,
                    document_id,
                    chunk_id,
                    content,
                    metadata,
                    1 - (embedding <=> %(query_embedding)s::vector) as similarity
                FROM document_embeddings
                WHERE 
                    (%(document_ids)s IS NULL OR document_id = ANY(%(document_ids)s))
                    AND (1 - (embedding <=> %(query_embedding)s::vector)) >= %(similarity_threshold)s
                    AND (%(metadata_filter)s IS NULL OR metadata @> %(metadata_filter)s::jsonb)
                ORDER BY embedding <=> %(query_embedding)s::vector
                LIMIT %(limit)s
            """,
            
            'vector_similarity_search_with_case': """
                SELECT 
                    de.id,
                    de.document_id,
                    de.chunk_id,
                    de.content,
                    de.metadata,
                    1 - (de.embedding <=> %(query_embedding)s::vector) as similarity,
                    d.filename,
                    d.status
                FROM document_embeddings de
                JOIN document d ON de.document_id = d.id
                WHERE 
                    d.case_id = %(case_id)s
                    AND d.status IN ('processed', 'enhanced')
                    AND (%(document_ids)s IS NULL OR de.document_id = ANY(%(document_ids)s))
                    AND (1 - (de.embedding <=> %(query_embedding)s::vector)) >= %(similarity_threshold)s
                    AND (%(metadata_filter)s IS NULL OR de.metadata @> %(metadata_filter)s::jsonb)
                ORDER BY de.embedding <=> %(query_embedding)s::vector
                LIMIT %(limit)s
            """,
            
            'batch_embedding_insert': """
                INSERT INTO document_embeddings (document_id, chunk_id, content, embedding, metadata)
                VALUES %s
                ON CONFLICT (document_id, chunk_id) 
                DO UPDATE SET
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata,
                    created_at = NOW()
                RETURNING id
            """,
            
            'document_chunks_by_case': """
                SELECT 
                    de.id,
                    de.document_id,
                    de.chunk_id,
                    de.content,
                    de.metadata,
                    d.filename,
                    d.status
                FROM document_embeddings de
                JOIN document d ON de.document_id = d.id
                WHERE 
                    d.case_id = %(case_id)s
                    AND d.status IN ('processed', 'enhanced')
                    AND (%(document_types)s IS NULL OR de.metadata->>'document_type' = ANY(%(document_types)s))
                ORDER BY de.created_at DESC
                LIMIT %(limit)s
            """,
            
            'embedding_stats': """
                SELECT 
                    COUNT(*) as total_embeddings,
                    COUNT(DISTINCT document_id) as unique_documents,
                    AVG(LENGTH(content)) as avg_content_length,
                    MAX(created_at) as last_updated
                FROM document_embeddings
                WHERE created_at >= NOW() - INTERVAL '24 hours'
            """
        }
    
    async def execute_optimized_similarity_search(self, 
                                                query_embedding: List[float],
                                                case_id: Optional[str] = None,
                                                document_ids: Optional[List[str]] = None,
                                                similarity_threshold: float = 0.5,
                                                metadata_filter: Optional[Dict] = None,
                                                limit: int = 10) -> List[Dict[str, Any]]:
        """Execute optimized vector similarity search"""
        
        # Create cache key
        import hashlib
        cache_key = hashlib.md5(
            f"{query_embedding[:5]}_{case_id}_{document_ids}_{similarity_threshold}_{limit}".encode()
        ).hexdigest()
        
        # Check cache first
        cached_result = self.query_cache.get(cache_key)
        if cached_result:
            self.query_metrics['similarity_search'].cache_hits += 1
            return cached_result
        
        start_time = time.time()
        
        try:
            # Choose appropriate query based on parameters
            if case_id:
                query = self.optimized_queries['vector_similarity_search_with_case']
            else:
                query = self.optimized_queries['vector_similarity_search']
            
            # Prepare parameters
            params = {
                'query_embedding': query_embedding,
                'document_ids': document_ids,
                'similarity_threshold': similarity_threshold,
                'metadata_filter': metadata_filter,
                'limit': limit
            }
            
            if case_id:
                params['case_id'] = case_id
            
            # Execute query
            async with self.connection_pool.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    results = cursor.fetchall()
            
            # Convert to list of dictionaries
            result_list = [dict(row) for row in results]
            
            # Cache results
            self.query_cache.set(cache_key, result_list)
            
            # Update metrics
            execution_time = time.time() - start_time
            metrics = self.query_metrics['similarity_search']
            metrics.query_count += 1
            metrics.total_execution_time += execution_time
            metrics.avg_execution_time = metrics.total_execution_time / metrics.query_count
            
            if execution_time > 1.0:
                metrics.slow_queries += 1
            
            logger.debug(f"Similarity search completed in {execution_time:.3f}s, {len(result_list)} results")
            
            return result_list
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.query_metrics['similarity_search'].failed_queries += 1
            logger.error(f"Similarity search failed after {execution_time:.3f}s: {e}")
            raise
    
    async def batch_insert_embeddings(self, embeddings_data: List[Dict[str, Any]]) -> List[int]:
        """Optimized batch insertion of embeddings"""
        if not embeddings_data:
            return []
        
        start_time = time.time()
        
        try:
            # Prepare data for batch insert
            values = []
            for item in embeddings_data:
                values.append((
                    item['document_id'],
                    item['chunk_id'],
                    item['content'],
                    item['embedding'],
                    item.get('metadata', {})
                ))
            
            # Execute batch insert
            async with self.connection_pool.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Use execute_values for efficient batch insert
                    from psycopg2.extras import execute_values
                    
                    query = """
                        INSERT INTO document_embeddings (document_id, chunk_id, content, embedding, metadata)
                        VALUES %s
                        ON CONFLICT (document_id, chunk_id) 
                        DO UPDATE SET
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata,
                            created_at = NOW()
                        RETURNING id
                    """
                    
                    execute_values(
                        cursor,
                        query,
                        values,
                        template=None,
                        page_size=100  # Process in batches of 100
                    )
                    
                    inserted_ids = cursor.fetchall()
                    conn.commit()
            
            # Update metrics
            execution_time = time.time() - start_time
            metrics = self.query_metrics['batch_insert']
            metrics.query_count += 1
            metrics.total_execution_time += execution_time
            metrics.avg_execution_time = metrics.total_execution_time / metrics.query_count
            
            if execution_time > 1.0:
                metrics.slow_queries += 1
            
            logger.info(f"Batch inserted {len(embeddings_data)} embeddings in {execution_time:.3f}s")
            
            return [row[0] for row in inserted_ids]
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.query_metrics['batch_insert'].failed_queries += 1
            logger.error(f"Batch insert failed after {execution_time:.3f}s: {e}")
            raise
    
    async def get_document_chunks_by_case(self, case_id: str, 
                                        document_types: Optional[List[str]] = None,
                                        limit: int = 100) -> List[Dict[str, Any]]:
        """Get document chunks for a specific case with optimization"""
        
        cache_key = f"case_chunks_{case_id}_{document_types}_{limit}"
        cached_result = self.query_cache.get(cache_key)
        if cached_result:
            self.query_metrics['case_chunks'].cache_hits += 1
            return cached_result
        
        start_time = time.time()
        
        try:
            params = {
                'case_id': case_id,
                'document_types': document_types,
                'limit': limit
            }
            
            async with self.connection_pool.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(self.optimized_queries['document_chunks_by_case'], params)
                    results = cursor.fetchall()
            
            result_list = [dict(row) for row in results]
            
            # Cache results for 5 minutes
            self.query_cache.set(cache_key, result_list)
            
            # Update metrics
            execution_time = time.time() - start_time
            metrics = self.query_metrics['case_chunks']
            metrics.query_count += 1
            metrics.total_execution_time += execution_time
            metrics.avg_execution_time = metrics.total_execution_time / metrics.query_count
            
            if execution_time > 1.0:
                metrics.slow_queries += 1
            
            return result_list
            
        except Exception as e:
            self.query_metrics['case_chunks'].failed_queries += 1
            logger.error(f"Get case chunks failed: {e}")
            raise
    
    async def optimize_database_indices(self) -> Dict[str, Any]:
        """Create and optimize database indices for better performance"""
        
        optimization_results = {
            'indices_created': [],
            'indices_updated': [],
            'errors': []
        }
        
        # Index definitions
        indices = [
            {
                'name': 'idx_embeddings_vector_cosine',
                'query': """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_embeddings_vector_cosine 
                    ON document_embeddings USING ivfflat (embedding vector_cosine_ops) 
                    WITH (lists = 100)
                """
            },
            {
                'name': 'idx_embeddings_doc_chunk',
                'query': """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_embeddings_doc_chunk 
                    ON document_embeddings (document_id, chunk_id)
                """
            },
            {
                'name': 'idx_embeddings_metadata_gin',
                'query': """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_embeddings_metadata_gin 
                    ON document_embeddings USING gin (metadata)
                """
            },
            {
                'name': 'idx_embeddings_created_at',
                'query': """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_embeddings_created_at 
                    ON document_embeddings (created_at DESC)
                """
            },
            {
                'name': 'idx_documents_case_status',
                'query': """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_case_status 
                    ON document (case_id, status) 
                    WHERE status IN ('processed', 'enhanced')
                """
            },
            {
                'name': 'idx_documents_filename_gin',
                'query': """
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_filename_gin 
                    ON document USING gin(to_tsvector('dutch', filename))
                """
            }
        ]
        
        try:
            async with self.connection_pool.get_connection() as conn:
                with conn.cursor() as cursor:
                    for index_def in indices:
                        try:
                            logger.info(f"Creating index: {index_def['name']}")
                            cursor.execute(index_def['query'])
                            conn.commit()
                            optimization_results['indices_created'].append(index_def['name'])
                        except Exception as e:
                            error_msg = f"Failed to create {index_def['name']}: {str(e)}"
                            logger.warning(error_msg)
                            optimization_results['errors'].append(error_msg)
                            conn.rollback()
                    
                    # Update table statistics
                    try:
                        logger.info("Updating table statistics...")
                        cursor.execute("ANALYZE document_embeddings")
                        cursor.execute("ANALYZE document")
                        conn.commit()
                        optimization_results['indices_updated'].append('table_statistics')
                    except Exception as e:
                        logger.warning(f"Failed to update statistics: {e}")
                        optimization_results['errors'].append(f"Statistics update failed: {str(e)}")
                        conn.rollback()
                    
                    # Set optimal configuration parameters
                    try:
                        logger.info("Optimizing PostgreSQL parameters...")
                        config_queries = [
                            "SET shared_preload_libraries = 'vector'",
                            "SET max_parallel_workers_per_gather = 2",
                            "SET effective_cache_size = '1GB'",
                            "SET random_page_cost = 1.1"
                        ]
                        
                        for config_query in config_queries:
                            try:
                                cursor.execute(config_query)
                            except Exception:
                                # Some settings might require restart, ignore
                                pass
                        
                        conn.commit()
                        optimization_results['indices_updated'].append('postgres_config')
                        
                    except Exception as e:
                        logger.warning(f"Failed to update PostgreSQL config: {e}")
                        optimization_results['errors'].append(f"Config update failed: {str(e)}")
            
            logger.info("Database optimization completed")
            return optimization_results
            
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            optimization_results['errors'].append(f"Optimization failed: {str(e)}")
            return optimization_results
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database performance statistics"""
        
        try:
            async with self.connection_pool.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Get embedding statistics
                    cursor.execute(self.optimized_queries['embedding_stats'])
                    embedding_stats = dict(cursor.fetchone())
                    
                    # Get table sizes
                    cursor.execute("""
                        SELECT 
                            schemaname,
                            tablename,
                            attname,
                            n_distinct,
                            correlation
                        FROM pg_stats 
                        WHERE tablename IN ('document_embeddings', 'document')
                        AND attname IN ('document_id', 'chunk_id', 'case_id', 'status')
                    """)
                    table_stats = cursor.fetchall()
                    
                    # Get index usage
                    cursor.execute("""
                        SELECT 
                            indexrelname as index_name,
                            idx_scan as scans,
                            idx_tup_read as tuples_read,
                            idx_tup_fetch as tuples_fetched
                        FROM pg_stat_user_indexes 
                        WHERE schemaname = 'public'
                        AND relname IN ('document_embeddings', 'document')
                        ORDER BY idx_scan DESC
                    """)
                    index_stats = cursor.fetchall()
                    
                    return {
                        'embedding_stats': embedding_stats,
                        'table_stats': [dict(row) for row in table_stats],
                        'index_stats': [dict(row) for row in index_stats],
                        'query_metrics': {
                            name: {
                                'query_count': metrics.query_count,
                                'avg_execution_time': metrics.avg_execution_time,
                                'slow_queries': metrics.slow_queries,
                                'failed_queries': metrics.failed_queries,
                                'cache_hits': metrics.cache_hits
                            }
                            for name, metrics in self.query_metrics.items()
                        },
                        'connection_pool_stats': self.connection_pool.get_pool_status(),
                        'cache_stats': self.query_cache.get_stats()
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {'error': str(e)}
    
    def clear_query_cache(self):
        """Clear the query cache"""
        self.query_cache.clear()
        logger.info("Query cache cleared")
    
    def close(self):
        """Close all database connections"""
        self.connection_pool.close()
        logger.info("Database optimizer closed")


# Singleton instance
_database_optimizer = None


def get_database_optimizer() -> DatabaseOptimizer:
    """Get the singleton database optimizer instance"""
    global _database_optimizer
    if _database_optimizer is None:
        _database_optimizer = DatabaseOptimizer()
    return _database_optimizer