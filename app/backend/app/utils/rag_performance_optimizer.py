"""
RAG Performance Optimizer for AI-Arbeidsdeskundige
Comprehensive performance optimization for RAG pipeline with caching, monitoring, and resource management
"""

import asyncio
import logging
import time
import gc
import psutil
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import hashlib
import threading
from contextlib import asynccontextmanager
import weakref

import numpy as np
from sqlalchemy import text
from sqlalchemy.pool import QueuePool

from app.core.config import settings
from app.db.database_service import get_database_service
from app.utils.vector_store_improved import get_hybrid_vector_store
from app.utils.embeddings import generate_embedding, generate_query_embedding

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics container"""
    query_count: int = 0
    total_query_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    embedding_generation_time: float = 0.0
    vector_search_time: float = 0.0
    database_query_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    active_connections: int = 0
    query_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    error_count: int = 0


@dataclass
class CacheConfig:
    """Cache configuration"""
    embedding_cache_size: int = 1000
    query_cache_size: int = 500
    result_cache_size: int = 200
    cache_ttl_seconds: int = 3600  # 1 hour
    enable_memory_cache: bool = True
    enable_redis_cache: bool = False


@dataclass
class OptimizationConfig:
    """Optimization configuration"""
    enable_query_batching: bool = True
    batch_size: int = 10
    batch_timeout_ms: int = 100
    enable_connection_pooling: bool = True
    max_connections: int = 20
    enable_prefetch: bool = True
    prefetch_size: int = 50
    enable_async_processing: bool = True
    worker_threads: int = 4


class IntelligentCache:
    """Multi-level intelligent caching system"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self._embedding_cache = {}
        self._query_cache = {}
        self._result_cache = {}
        self._cache_stats = defaultdict(int)
        self._lock = threading.RLock()
        
        # Cache expiry tracking
        self._cache_expiry = {
            'embeddings': {},
            'queries': {},
            'results': {}
        }
        
        # Memory monitoring
        self._memory_threshold_mb = 500  # Clear cache if memory usage exceeds this
        
    def _is_expired(self, cache_type: str, key: str) -> bool:
        """Check if cache entry is expired"""
        expiry_time = self._cache_expiry[cache_type].get(key)
        if not expiry_time:
            return False
        return datetime.now() > expiry_time
    
    def _cleanup_expired(self, cache_type: str) -> None:
        """Remove expired entries from cache"""
        current_time = datetime.now()
        expired_keys = []
        
        for key, expiry_time in self._cache_expiry[cache_type].items():
            if current_time > expiry_time:
                expired_keys.append(key)
        
        cache_map = {
            'embeddings': self._embedding_cache,
            'queries': self._query_cache,
            'results': self._result_cache
        }
        
        target_cache = cache_map[cache_type]
        for key in expired_keys:
            target_cache.pop(key, None)
            self._cache_expiry[cache_type].pop(key, None)
    
    def _enforce_size_limit(self, cache_type: str) -> None:
        """Enforce cache size limits using LRU eviction"""
        cache_map = {
            'embeddings': (self._embedding_cache, self.config.embedding_cache_size),
            'queries': (self._query_cache, self.config.query_cache_size),
            'results': (self._result_cache, self.config.result_cache_size)
        }
        
        target_cache, size_limit = cache_map[cache_type]
        
        if len(target_cache) > size_limit:
            # Simple FIFO eviction (could be improved to true LRU)
            excess = len(target_cache) - size_limit
            keys_to_remove = list(target_cache.keys())[:excess]
            
            for key in keys_to_remove:
                target_cache.pop(key, None)
                self._cache_expiry[cache_type].pop(key, None)
    
    def get_embedding(self, text: str, text_hash: str = None) -> Optional[List[float]]:
        """Get embedding from cache"""
        if not text_hash:
            text_hash = hashlib.md5(text.encode()).hexdigest()
        
        with self._lock:
            if text_hash in self._embedding_cache and not self._is_expired('embeddings', text_hash):
                self._cache_stats['embedding_hits'] += 1
                return self._embedding_cache[text_hash]
            
            self._cache_stats['embedding_misses'] += 1
            return None
    
    def set_embedding(self, text: str, embedding: List[float], text_hash: str = None) -> None:
        """Store embedding in cache"""
        if not text_hash:
            text_hash = hashlib.md5(text.encode()).hexdigest()
        
        with self._lock:
            self._cleanup_expired('embeddings')
            self._embedding_cache[text_hash] = embedding
            self._cache_expiry['embeddings'][text_hash] = datetime.now() + timedelta(seconds=self.config.cache_ttl_seconds)
            self._enforce_size_limit('embeddings')
    
    def get_query_result(self, query_key: str) -> Optional[Dict[str, Any]]:
        """Get query result from cache"""
        with self._lock:
            if query_key in self._query_cache and not self._is_expired('queries', query_key):
                self._cache_stats['query_hits'] += 1
                return self._query_cache[query_key]
            
            self._cache_stats['query_misses'] += 1
            return None
    
    def set_query_result(self, query_key: str, result: Dict[str, Any]) -> None:
        """Store query result in cache"""
        with self._lock:
            self._cleanup_expired('queries')
            self._query_cache[query_key] = result
            self._cache_expiry['queries'][query_key] = datetime.now() + timedelta(seconds=self.config.cache_ttl_seconds)
            self._enforce_size_limit('queries')
    
    def get_search_result(self, search_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get search result from cache"""
        with self._lock:
            if search_key in self._result_cache and not self._is_expired('results', search_key):
                self._cache_stats['result_hits'] += 1
                return self._result_cache[search_key]
            
            self._cache_stats['result_misses'] += 1
            return None
    
    def set_search_result(self, search_key: str, results: List[Dict[str, Any]]) -> None:
        """Store search results in cache"""
        with self._lock:
            self._cleanup_expired('results')
            self._result_cache[search_key] = results
            self._cache_expiry['results'][search_key] = datetime.now() + timedelta(seconds=self.config.cache_ttl_seconds)
            self._enforce_size_limit('results')
    
    def clear_cache(self, cache_type: str = None) -> None:
        """Clear cache (all or specific type)"""
        with self._lock:
            if cache_type == 'embeddings' or cache_type is None:
                self._embedding_cache.clear()
                self._cache_expiry['embeddings'].clear()
            if cache_type == 'queries' or cache_type is None:
                self._query_cache.clear()
                self._cache_expiry['queries'].clear()
            if cache_type == 'results' or cache_type is None:
                self._result_cache.clear()
                self._cache_expiry['results'].clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_hits = sum(self._cache_stats[key] for key in ['embedding_hits', 'query_hits', 'result_hits'])
            total_requests = sum(self._cache_stats.values())
            
            return {
                'cache_sizes': {
                    'embeddings': len(self._embedding_cache),
                    'queries': len(self._query_cache),
                    'results': len(self._result_cache)
                },
                'hit_rates': {
                    'embeddings': self._cache_stats['embedding_hits'] / max(self._cache_stats['embedding_hits'] + self._cache_stats['embedding_misses'], 1),
                    'queries': self._cache_stats['query_hits'] / max(self._cache_stats['query_hits'] + self._cache_stats['query_misses'], 1),
                    'results': self._cache_stats['result_hits'] / max(self._cache_stats['result_hits'] + self._cache_stats['result_misses'], 1),
                    'overall': total_hits / max(total_requests, 1)
                },
                'stats': dict(self._cache_stats)
            }


class ConnectionManager:
    """Intelligent database connection management"""
    
    def __init__(self, max_connections: int = 20):
        self.max_connections = max_connections
        self._connection_pool = asyncio.Queue(maxsize=max_connections)
        self._active_connections = 0
        self._connection_stats = defaultdict(int)
        self._lock = asyncio.Lock()
        
    async def _create_connection(self):
        """Create a new database connection"""
        from app.db.postgres import get_db
        return next(get_db())
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool"""
        connection = None
        try:
            async with self._lock:
                if not self._connection_pool.empty():
                    connection = await self._connection_pool.get()
                    self._connection_stats['reused'] += 1
                elif self._active_connections < self.max_connections:
                    connection = await self._create_connection()
                    self._active_connections += 1
                    self._connection_stats['created'] += 1
                else:
                    # Wait for a connection to become available
                    connection = await self._connection_pool.get()
                    self._connection_stats['waited'] += 1
            
            yield connection
            
        finally:
            if connection:
                # Return connection to pool
                if self._connection_pool.qsize() < self.max_connections // 2:
                    await self._connection_pool.put(connection)
                else:
                    # Close excess connections
                    try:
                        connection.close()
                    except:
                        pass
                    async with self._lock:
                        self._active_connections -= 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            'active_connections': self._active_connections,
            'max_connections': self.max_connections,
            'pool_size': self._connection_pool.qsize(),
            'connection_stats': dict(self._connection_stats)
        }


class QueryBatcher:
    """Batch similar queries for improved performance"""
    
    def __init__(self, batch_size: int = 10, timeout_ms: int = 100):
        self.batch_size = batch_size
        self.timeout_ms = timeout_ms
        self._pending_queries = []
        self._query_futures = {}
        self._lock = asyncio.Lock()
        self._batch_task = None
    
    async def add_query(self, query_id: str, query_data: Dict[str, Any]) -> Any:
        """Add query to batch and return future result"""
        future = asyncio.Future()
        
        async with self._lock:
            self._pending_queries.append({
                'id': query_id,
                'data': query_data,
                'future': future,
                'timestamp': time.time()
            })
            self._query_futures[query_id] = future
            
            # Start batch processing if not already running
            if not self._batch_task or self._batch_task.done():
                self._batch_task = asyncio.create_task(self._process_batch())
        
        return await future
    
    async def _process_batch(self):
        """Process batched queries"""
        await asyncio.sleep(self.timeout_ms / 1000)  # Wait for batch to fill
        
        async with self._lock:
            if not self._pending_queries:
                return
            
            current_batch = self._pending_queries.copy()
            self._pending_queries.clear()
        
        # Group similar queries
        query_groups = self._group_similar_queries(current_batch)
        
        # Process each group
        for group in query_groups:
            try:
                results = await self._execute_batch(group)
                
                # Set results for all queries in the group
                for i, query in enumerate(group):
                    query['future'].set_result(results[i])
                    
            except Exception as e:
                # Set exception for all queries in the group
                for query in group:
                    query['future'].set_exception(e)
    
    def _group_similar_queries(self, queries: List[Dict]) -> List[List[Dict]]:
        """Group similar queries for batch processing"""
        groups = []
        used_indices = set()
        
        for i, query in enumerate(queries):
            if i in used_indices:
                continue
                
            group = [query]
            used_indices.add(i)
            
            # Find similar queries
            for j, other_query in enumerate(queries[i+1:], start=i+1):
                if j in used_indices:
                    continue
                    
                if self._queries_similar(query, other_query):
                    group.append(other_query)
                    used_indices.add(j)
                    
                if len(group) >= self.batch_size:
                    break
            
            groups.append(group)
        
        return groups
    
    def _queries_similar(self, query1: Dict, query2: Dict) -> bool:
        """Check if two queries are similar enough to batch"""
        # Simple similarity check based on query type and parameters
        data1 = query1.get('data', {})
        data2 = query2.get('data', {})
        
        return (
            data1.get('query_type') == data2.get('query_type') and
            data1.get('case_id') == data2.get('case_id') and
            abs(len(data1.get('query', '')) - len(data2.get('query', ''))) < 100
        )
    
    async def _execute_batch(self, queries: List[Dict]) -> List[Any]:
        """Execute a batch of queries"""
        # This would be implemented to handle the specific query types
        # For now, we'll just execute them individually
        results = []
        for query in queries:
            # Placeholder - would call the appropriate processing function
            result = await self._execute_single_query(query['data'])
            results.append(result)
        return results
    
    async def _execute_single_query(self, query_data: Dict[str, Any]) -> Any:
        """Execute a single query - placeholder"""
        # This would be replaced with actual query execution logic
        await asyncio.sleep(0.01)  # Simulate processing
        return {'result': 'processed', 'query': query_data}


class RAGPerformanceOptimizer:
    """Main RAG performance optimization class"""
    
    def __init__(self):
        self.db_service = get_database_service()
        self.vector_store = get_hybrid_vector_store(self.db_service)
        
        # Configuration
        self.cache_config = CacheConfig()
        self.optimization_config = OptimizationConfig()
        
        # Components
        self.cache = IntelligentCache(self.cache_config)
        self.connection_manager = ConnectionManager(self.optimization_config.max_connections)
        self.query_batcher = QueryBatcher(
            self.optimization_config.batch_size,
            self.optimization_config.batch_timeout_ms
        )
        
        # Performance tracking
        self.metrics = PerformanceMetrics()
        self._start_time = time.time()
        
        # Background tasks
        self._monitoring_task = None
        self._cleanup_task = None
        
        logger.info("RAG Performance Optimizer initialized")
    
    async def start_background_tasks(self):
        """Start background monitoring and cleanup tasks"""
        if not self._monitoring_task or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitor_performance())
        
        if not self._cleanup_task or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_resources())
    
    async def stop_background_tasks(self):
        """Stop background tasks"""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
        
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
    
    async def _monitor_performance(self):
        """Background performance monitoring"""
        while True:
            try:
                # Update system metrics
                process = psutil.Process()
                self.metrics.memory_usage_mb = process.memory_info().rss / 1024 / 1024
                self.metrics.cpu_usage_percent = process.cpu_percent()
                
                # Log performance stats every 5 minutes
                if int(time.time()) % 300 == 0:
                    stats = self.get_performance_stats()
                    logger.info(f"Performance stats: {json.dumps(stats, indent=2)}")
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_resources(self):
        """Background resource cleanup"""
        while True:
            try:
                # Clean up cache if memory usage is high
                if self.metrics.memory_usage_mb > self.cache._memory_threshold_mb:
                    logger.info("High memory usage detected, clearing cache")
                    self.cache.clear_cache()
                    gc.collect()
                
                # Regular garbage collection
                gc.collect()
                
                await asyncio.sleep(300)  # Clean every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in resource cleanup: {e}")
                await asyncio.sleep(300)
    
    async def optimized_embedding_generation(self, text: str, force_refresh: bool = False) -> List[float]:
        """Generate embedding with caching and optimization"""
        start_time = time.time()
        
        try:
            # Create cache key
            text_hash = hashlib.md5(text.encode()).hexdigest()
            
            # Check cache first
            if not force_refresh:
                cached_embedding = self.cache.get_embedding(text, text_hash)
                if cached_embedding:
                    return cached_embedding
            
            # Generate new embedding
            embedding = await asyncio.to_thread(generate_embedding, text)
            
            # Cache the result
            self.cache.set_embedding(text, embedding, text_hash)
            
            return embedding
            
        except Exception as e:
            self.metrics.error_count += 1
            logger.error(f"Error generating embedding: {e}")
            raise
        finally:
            generation_time = time.time() - start_time
            self.metrics.embedding_generation_time += generation_time
    
    async def optimized_vector_search(self, query_embedding: List[float], 
                                    limit: int = 10, 
                                    filters: Dict[str, Any] = None,
                                    similarity_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """Optimized vector search with caching and batching"""
        start_time = time.time()
        
        try:
            # Create search key for caching
            search_key = self._create_search_key(query_embedding, limit, filters, similarity_threshold)
            
            # Check cache
            cached_results = self.cache.get_search_result(search_key)
            if cached_results:
                return cached_results
            
            # Perform search using connection manager
            async with self.connection_manager.get_connection() as conn:
                # Execute optimized vector search
                from app.utils.vector_store_improved import similarity_search
                results = await asyncio.to_thread(
                    similarity_search,
                    query_embedding=query_embedding,
                    limit=limit,
                    similarity_threshold=similarity_threshold,
                    filter_dict=filters,
                    timeout=30
                )
            
            # Cache results
            self.cache.set_search_result(search_key, results)
            
            return results
            
        except Exception as e:
            self.metrics.error_count += 1
            logger.error(f"Error in vector search: {e}")
            raise
        finally:
            search_time = time.time() - start_time
            self.metrics.vector_search_time += search_time
    
    async def optimized_hybrid_search(self, query: str, 
                                    case_id: str = None,
                                    document_ids: List[str] = None,
                                    limit: int = 10) -> Dict[str, Any]:
        """Optimized hybrid search combining multiple strategies"""
        start_time = time.time()
        
        try:
            self.metrics.query_count += 1
            
            # Create query key for caching
            query_key = self._create_query_key(query, case_id, document_ids, limit)
            
            # Check cache
            cached_result = self.cache.get_query_result(query_key)
            if cached_result:
                return cached_result
            
            # Generate query embedding with caching
            query_embedding = await self.optimized_embedding_generation(query)
            
            # Perform hybrid search with optimization
            from app.utils.hybrid_search import hybrid_search_documents
            
            # Use async execution
            result = await asyncio.to_thread(
                hybrid_search_documents,
                query=query,
                case_id=case_id,
                document_ids=document_ids,
                limit=limit
            )
            
            # Cache result
            self.cache.set_query_result(query_key, result)
            
            return result
            
        except Exception as e:
            self.metrics.error_count += 1
            logger.error(f"Error in hybrid search: {e}")
            raise
        finally:
            query_time = time.time() - start_time
            self.metrics.total_query_time += query_time
            self.metrics.query_times.append(query_time)
    
    async def batch_process_documents(self, documents: List[Dict[str, Any]],
                                    batch_size: int = None) -> Dict[str, Any]:
        """Batch process multiple documents for optimal performance"""
        if not batch_size:
            batch_size = self.optimization_config.batch_size
        
        start_time = time.time()
        results = {
            'processed': 0,
            'errors': 0,
            'processing_times': [],
            'results': []
        }
        
        try:
            # Process documents in batches
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                batch_start_time = time.time()
                
                # Process batch concurrently
                tasks = []
                for doc in batch:
                    task = asyncio.create_task(self._process_single_document(doc))
                    tasks.append(task)
                
                # Wait for batch completion
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for result in batch_results:
                    if isinstance(result, Exception):
                        results['errors'] += 1
                        logger.error(f"Document processing error: {result}")
                    else:
                        results['processed'] += 1
                        results['results'].append(result)
                
                batch_time = time.time() - batch_start_time
                results['processing_times'].append(batch_time)
                
                # Brief pause between batches to prevent overload
                await asyncio.sleep(0.1)
        
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            raise
        
        total_time = time.time() - start_time
        results['total_time'] = total_time
        
        return results
    
    async def _process_single_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single document optimally"""
        doc_id = document.get('id')
        content = document.get('content', '')
        
        # Generate embeddings for document chunks
        chunks = self._create_optimized_chunks(content)
        embeddings = []
        
        for chunk in chunks:
            embedding = await self.optimized_embedding_generation(chunk['content'])
            embeddings.append(embedding)
        
        return {
            'document_id': doc_id,
            'chunks_processed': len(chunks),
            'embeddings_generated': len(embeddings),
            'content_length': len(content)
        }
    
    def _create_optimized_chunks(self, content: str, 
                               chunk_size: int = None,
                               overlap: int = None) -> List[Dict[str, Any]]:
        """Create optimized chunks based on content characteristics"""
        if not chunk_size:
            chunk_size = settings.CHUNK_SIZE
        if not overlap:
            overlap = settings.CHUNK_OVERLAP
        
        # Intelligent chunking based on content structure
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = ""
        current_size = 0
        
        for paragraph in paragraphs:
            # Check if adding paragraph would exceed chunk size
            if current_size + len(paragraph) > chunk_size and current_chunk:
                # Save current chunk
                chunks.append({
                    'content': current_chunk.strip(),
                    'size': len(current_chunk),
                    'type': 'paragraph_based'
                })
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk, overlap)
                current_chunk = overlap_text + "\n\n" + paragraph
                current_size = len(current_chunk)
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
                current_size += len(paragraph)
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                'content': current_chunk.strip(),
                'size': len(current_chunk),
                'type': 'paragraph_based'
            })
        
        return chunks
    
    def _get_overlap_text(self, text: str, overlap_size: int) -> str:
        """Get overlap text for chunk continuity"""
        if len(text) <= overlap_size:
            return text
        return text[-overlap_size:]
    
    def _create_search_key(self, query_embedding: List[float], 
                          limit: int, filters: Dict[str, Any], 
                          similarity_threshold: float) -> str:
        """Create cache key for search results"""
        # Create hash from embedding (first 10 values for performance)
        embedding_hash = hashlib.md5(str(query_embedding[:10]).encode()).hexdigest()[:8]
        filter_hash = hashlib.md5(str(sorted(filters.items()) if filters else "").encode()).hexdigest()[:8]
        
        return f"search_{embedding_hash}_{limit}_{filter_hash}_{similarity_threshold}"
    
    def _create_query_key(self, query: str, case_id: str, 
                         document_ids: List[str], limit: int) -> str:
        """Create cache key for query results"""
        doc_ids_str = "_".join(sorted(document_ids)) if document_ids else ""
        key_data = f"{query}_{case_id}_{doc_ids_str}_{limit}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        uptime = time.time() - self._start_time
        avg_query_time = self.metrics.total_query_time / max(self.metrics.query_count, 1)
        
        # Calculate query time percentiles
        query_times = list(self.metrics.query_times)
        query_times.sort()
        
        percentiles = {}
        if query_times:
            percentiles = {
                'p50': query_times[len(query_times) // 2],
                'p90': query_times[int(len(query_times) * 0.9)],
                'p95': query_times[int(len(query_times) * 0.95)],
                'p99': query_times[int(len(query_times) * 0.99)]
            }
        
        return {
            'uptime_seconds': uptime,
            'query_metrics': {
                'total_queries': self.metrics.query_count,
                'average_query_time': avg_query_time,
                'total_query_time': self.metrics.total_query_time,
                'error_rate': self.metrics.error_count / max(self.metrics.query_count, 1),
                'query_time_percentiles': percentiles
            },
            'cache_metrics': self.cache.get_stats(),
            'connection_metrics': self.connection_manager.get_stats(),
            'system_metrics': {
                'memory_usage_mb': self.metrics.memory_usage_mb,
                'cpu_usage_percent': self.metrics.cpu_usage_percent
            },
            'component_timings': {
                'embedding_generation_time': self.metrics.embedding_generation_time,
                'vector_search_time': self.metrics.vector_search_time,
                'database_query_time': self.metrics.database_query_time
            }
        }
    
    async def warm_up_cache(self, common_queries: List[str] = None):
        """Warm up the cache with common queries"""
        if not common_queries:
            common_queries = [
                "belastbaarheid fysiek",
                "beperkingen werkhervatting",
                "mogelijkheden arbeid",
                "medische diagnose",
                "arbeidsdeskundige advies",
                "re-integratie perspectief"
            ]
        
        logger.info(f"Warming up cache with {len(common_queries)} queries")
        
        for query in common_queries:
            try:
                await self.optimized_embedding_generation(query)
                logger.debug(f"Cached embedding for: {query}")
            except Exception as e:
                logger.error(f"Error warming up cache for query '{query}': {e}")
    
    async def optimize_database_indices(self):
        """Optimize database indices for better performance"""
        try:
            async with self.connection_manager.get_connection() as conn:
                # Create optimized indices for vector operations
                index_queries = [
                    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_doc_embeddings_similarity ON document_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);",
                    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_doc_embeddings_metadata_gin ON document_embeddings USING gin (metadata);",
                    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_doc_embeddings_doc_id_chunk ON document_embeddings (document_id, chunk_id);",
                    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_case_status ON document (case_id, status) WHERE status IN ('processed', 'enhanced');"
                ]
                
                for query in index_queries:
                    try:
                        await conn.execute(text(query))
                        await conn.commit()
                        logger.info(f"Created index: {query.split()[4]}")
                    except Exception as e:
                        logger.warning(f"Index creation skipped (may already exist): {e}")
                
                # Update table statistics
                await conn.execute(text("ANALYZE document_embeddings;"))
                await conn.execute(text("ANALYZE document;"))
                await conn.commit()
                
                logger.info("Database optimization completed")
                
        except Exception as e:
            logger.error(f"Error optimizing database indices: {e}")
    
    def clear_all_caches(self):
        """Clear all caches"""
        self.cache.clear_cache()
        logger.info("All caches cleared")
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down RAG Performance Optimizer")
        await self.stop_background_tasks()
        self.clear_all_caches()


# Singleton instance
_performance_optimizer = None


def get_performance_optimizer() -> RAGPerformanceOptimizer:
    """Get the singleton performance optimizer instance"""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = RAGPerformanceOptimizer()
    return _performance_optimizer


async def initialize_performance_optimizer():
    """Initialize the performance optimizer with background tasks"""
    optimizer = get_performance_optimizer()
    await optimizer.start_background_tasks()
    await optimizer.warm_up_cache()
    await optimizer.optimize_database_indices()
    return optimizer