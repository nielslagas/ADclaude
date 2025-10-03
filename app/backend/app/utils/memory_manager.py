"""
Memory Manager and Resource Optimizer for RAG Pipeline
Intelligent memory management, garbage collection, and resource optimization for large-scale document processing
"""

import gc
import os
import sys
import psutil
import threading
import weakref
import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from contextlib import contextmanager
from collections import defaultdict, deque
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class MemoryStats:
    """Memory statistics container"""
    total_memory_mb: float = 0.0
    available_memory_mb: float = 0.0
    used_memory_mb: float = 0.0
    memory_percent: float = 0.0
    process_memory_mb: float = 0.0
    process_memory_percent: float = 0.0
    swap_memory_mb: float = 0.0
    gc_collections: Dict[int, int] = field(default_factory=dict)
    large_objects_count: int = 0


@dataclass
class ResourceLimits:
    """Resource usage limits"""
    max_memory_mb: float = 2048  # 2GB
    max_memory_percent: float = 80.0  # 80% of available memory
    max_embedding_cache_size: int = 1000
    max_chunk_cache_size: int = 500
    gc_threshold_mb: float = 100  # Trigger GC when memory increases by 100MB
    emergency_cleanup_threshold_mb: float = 1500  # Emergency cleanup at 1.5GB


class MemoryAwareCache:
    """Memory-aware caching system that respects memory limits"""
    
    def __init__(self, name: str, max_size: int, max_memory_mb: float = 100):
        self.name = name
        self.max_size = max_size
        self.max_memory_mb = max_memory_mb
        self._cache = {}
        self._access_times = {}
        self._memory_usage = 0.0
        self._lock = threading.RLock()
        
        # Weak references for automatic cleanup
        self._cleanup_callbacks = []
    
    def _estimate_size(self, obj: Any) -> float:
        """Estimate object size in MB"""
        try:
            if isinstance(obj, (str, bytes)):
                return len(obj) / (1024 * 1024)
            elif isinstance(obj, (list, tuple)):
                if obj and isinstance(obj[0], (int, float)):
                    # Assume numeric list/array
                    return len(obj) * 8 / (1024 * 1024)  # 8 bytes per number
                else:
                    # Estimate based on string representation
                    return len(str(obj)) / (1024 * 1024)
            elif isinstance(obj, dict):
                return len(str(obj)) / (1024 * 1024)
            elif hasattr(obj, '__sizeof__'):
                return obj.__sizeof__() / (1024 * 1024)
            else:
                return sys.getsizeof(obj) / (1024 * 1024)
        except:
            return 0.1  # Default small size
    
    def _evict_lru(self, target_memory: float) -> None:
        """Evict least recently used items to free memory"""
        if not self._access_times:
            return
        
        # Sort by access time (oldest first)
        sorted_items = sorted(self._access_times.items(), key=lambda x: x[1])
        memory_freed = 0.0
        
        for key, _ in sorted_items:
            if memory_freed >= target_memory:
                break
            
            if key in self._cache:
                obj_size = self._estimate_size(self._cache[key])
                del self._cache[key]
                del self._access_times[key]
                memory_freed += obj_size
                self._memory_usage -= obj_size
        
        logger.debug(f"Cache {self.name}: Evicted {memory_freed:.2f}MB, {len(sorted_items)} items")
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        with self._lock:
            if key in self._cache:
                self._access_times[key] = time.time()
                return self._cache[key]
            return None
    
    def set(self, key: str, value: Any) -> bool:
        """Set item in cache, returns True if successful"""
        with self._lock:
            # Estimate memory needed
            value_size = self._estimate_size(value)
            
            # Check if we need to make room
            if len(self._cache) >= self.max_size:
                self._evict_lru(value_size)
            
            if self._memory_usage + value_size > self.max_memory_mb:
                # Try to free enough memory
                target_free = (self._memory_usage + value_size) - self.max_memory_mb * 0.8
                self._evict_lru(target_free)
                
                # Check if we still can't fit it
                if self._memory_usage + value_size > self.max_memory_mb:
                    logger.warning(f"Cache {self.name}: Cannot cache item of size {value_size:.2f}MB")
                    return False
            
            # Add to cache
            if key in self._cache:
                old_size = self._estimate_size(self._cache[key])
                self._memory_usage -= old_size
            
            self._cache[key] = value
            self._access_times[key] = time.time()
            self._memory_usage += value_size
            
            return True
    
    def clear(self) -> None:
        """Clear all cached items"""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
            self._memory_usage = 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                'name': self.name,
                'size': len(self._cache),
                'max_size': self.max_size,
                'memory_usage_mb': self._memory_usage,
                'max_memory_mb': self.max_memory_mb,
                'memory_efficiency': self._memory_usage / max(self.max_memory_mb, 1)
            }


class ObjectPool:
    """Object pool for reusing expensive-to-create objects"""
    
    def __init__(self, factory: Callable[[], Any], max_size: int = 10):
        self.factory = factory
        self.max_size = max_size
        self._pool = deque()
        self._lock = threading.Lock()
        self._created_count = 0
        self._reused_count = 0
    
    @contextmanager
    def get_object(self):
        """Get object from pool or create new one"""
        obj = None
        created = False
        
        with self._lock:
            if self._pool:
                obj = self._pool.popleft()
                self._reused_count += 1
            else:
                obj = self.factory()
                self._created_count += 1
                created = True
        
        try:
            # Reset object if needed
            if hasattr(obj, 'reset'):
                obj.reset()
            
            yield obj
            
        finally:
            # Return to pool if not created fresh and pool not full
            with self._lock:
                if not created and len(self._pool) < self.max_size:
                    self._pool.append(obj)
                elif created:
                    # Clean up newly created object if pool is full
                    if hasattr(obj, 'close'):
                        obj.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        with self._lock:
            total_requests = self._created_count + self._reused_count
            return {
                'pool_size': len(self._pool),
                'max_size': self.max_size,
                'created_count': self._created_count,
                'reused_count': self._reused_count,
                'reuse_rate': self._reused_count / max(total_requests, 1),
                'efficiency': len(self._pool) / self.max_size
            }


class MemoryManager:
    """Comprehensive memory management system"""
    
    def __init__(self, resource_limits: Optional[ResourceLimits] = None):
        self.limits = resource_limits or ResourceLimits()
        self.stats = MemoryStats()
        
        # Memory-aware caches
        self.embedding_cache = MemoryAwareCache("embeddings", 1000, 200)
        self.chunk_cache = MemoryAwareCache("chunks", 500, 100)
        self.result_cache = MemoryAwareCache("results", 200, 50)
        
        # Object pools
        self.numpy_pool = ObjectPool(lambda: np.array([]), 5)
        
        # Monitoring
        self._monitoring_enabled = False
        self._monitoring_task = None
        self._last_gc_memory = 0.0
        self._memory_history = deque(maxlen=100)
        
        # Cleanup callbacks
        self._cleanup_callbacks = []
        
        logger.info(f"Memory manager initialized with limits: {self.limits.max_memory_mb}MB")
    
    def get_memory_stats(self) -> MemoryStats:
        """Get current memory statistics"""
        try:
            # System memory
            memory = psutil.virtual_memory()
            self.stats.total_memory_mb = memory.total / (1024 * 1024)
            self.stats.available_memory_mb = memory.available / (1024 * 1024)
            self.stats.used_memory_mb = memory.used / (1024 * 1024)
            self.stats.memory_percent = memory.percent
            
            # Process memory
            process = psutil.Process()
            process_memory = process.memory_info()
            self.stats.process_memory_mb = process_memory.rss / (1024 * 1024)
            self.stats.process_memory_percent = (process_memory.rss / memory.total) * 100
            
            # Swap memory
            swap = psutil.swap_memory()
            self.stats.swap_memory_mb = swap.used / (1024 * 1024)
            
            # Garbage collection stats
            self.stats.gc_collections = {i: gc.get_count()[i] for i in range(3)}
            
            # Count large objects
            self.stats.large_objects_count = len([obj for obj in gc.get_objects() 
                                                if sys.getsizeof(obj) > 1024 * 1024])  # > 1MB
            
            return self.stats
            
        except Exception as e:
            logger.warning(f"Failed to get memory stats: {e}")
            return self.stats
    
    def is_memory_pressure(self) -> bool:
        """Check if system is under memory pressure"""
        stats = self.get_memory_stats()
        
        return (
            stats.process_memory_mb > self.limits.max_memory_mb or
            stats.memory_percent > self.limits.max_memory_percent or
            stats.process_memory_percent > 15.0  # Process using > 15% of system memory
        )
    
    def trigger_garbage_collection(self, level: int = 2) -> Dict[str, Any]:
        """Trigger garbage collection and return statistics"""
        start_time = time.time()
        initial_stats = self.get_memory_stats()
        
        # Force garbage collection
        collected_objects = []
        for generation in range(level + 1):
            collected = gc.collect(generation)
            collected_objects.append(collected)
        
        # Get stats after GC
        final_stats = self.get_memory_stats()
        gc_time = time.time() - start_time
        
        memory_freed = initial_stats.process_memory_mb - final_stats.process_memory_mb
        
        gc_stats = {
            'gc_time': gc_time,
            'memory_freed_mb': memory_freed,
            'collected_objects': collected_objects,
            'initial_memory_mb': initial_stats.process_memory_mb,
            'final_memory_mb': final_stats.process_memory_mb
        }
        
        logger.info(f"GC completed: freed {memory_freed:.2f}MB in {gc_time:.3f}s")
        return gc_stats
    
    def emergency_cleanup(self) -> Dict[str, Any]:
        """Perform emergency memory cleanup"""
        logger.warning("Performing emergency memory cleanup")
        
        cleanup_stats = {
            'caches_cleared': 0,
            'callbacks_executed': 0,
            'memory_freed_mb': 0.0
        }
        
        initial_memory = self.get_memory_stats().process_memory_mb
        
        # Clear all caches
        self.embedding_cache.clear()
        self.chunk_cache.clear()
        self.result_cache.clear()
        cleanup_stats['caches_cleared'] = 3
        
        # Execute cleanup callbacks
        for callback in self._cleanup_callbacks:
            try:
                callback()
                cleanup_stats['callbacks_executed'] += 1
            except Exception as e:
                logger.warning(f"Cleanup callback failed: {e}")
        
        # Force aggressive garbage collection
        gc_stats = self.trigger_garbage_collection(2)
        
        final_memory = self.get_memory_stats().process_memory_mb
        cleanup_stats['memory_freed_mb'] = initial_memory - final_memory
        
        logger.warning(f"Emergency cleanup freed {cleanup_stats['memory_freed_mb']:.2f}MB")
        return cleanup_stats
    
    def register_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """Register a cleanup callback for emergency situations"""
        self._cleanup_callbacks.append(callback)
    
    @contextmanager
    def memory_limit_context(self, max_memory_mb: float):
        """Context manager that enforces memory limits"""
        original_limit = self.limits.max_memory_mb
        self.limits.max_memory_mb = max_memory_mb
        
        try:
            yield
        finally:
            self.limits.max_memory_mb = original_limit
            
            # Check if we exceeded limit during execution
            if self.is_memory_pressure():
                self.trigger_garbage_collection()
    
    def optimize_for_large_processing(self) -> None:
        """Optimize memory settings for large document processing"""
        logger.info("Optimizing memory for large document processing")
        
        # Reduce cache sizes
        self.embedding_cache.max_size = min(500, self.embedding_cache.max_size)
        self.embedding_cache.max_memory_mb = min(100, self.embedding_cache.max_memory_mb)
        
        self.chunk_cache.max_size = min(200, self.chunk_cache.max_size)
        self.chunk_cache.max_memory_mb = min(50, self.chunk_cache.max_memory_mb)
        
        # More aggressive GC
        gc.set_threshold(100, 5, 5)  # More frequent GC
        
        # Clear existing caches
        self.embedding_cache.clear()
        self.chunk_cache.clear()
        
        self.trigger_garbage_collection()
    
    def optimize_for_speed(self) -> None:
        """Optimize memory settings for speed (use more memory)"""
        logger.info("Optimizing memory for speed")
        
        # Increase cache sizes if memory allows
        if not self.is_memory_pressure():
            self.embedding_cache.max_size = min(2000, self.limits.max_embedding_cache_size)
            self.embedding_cache.max_memory_mb = min(400, self.limits.max_memory_mb * 0.2)
            
            self.chunk_cache.max_size = min(1000, self.limits.max_chunk_cache_size)
            self.chunk_cache.max_memory_mb = min(200, self.limits.max_memory_mb * 0.1)
        
        # Less aggressive GC
        gc.set_threshold(700, 10, 10)
    
    async def start_monitoring(self, interval_seconds: int = 30) -> None:
        """Start background memory monitoring"""
        if self._monitoring_enabled:
            return
        
        self._monitoring_enabled = True
        self._monitoring_task = asyncio.create_task(self._monitor_memory(interval_seconds))
        logger.info(f"Memory monitoring started (interval: {interval_seconds}s)")
    
    async def stop_monitoring(self) -> None:
        """Stop background memory monitoring"""
        self._monitoring_enabled = False
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
        logger.info("Memory monitoring stopped")
    
    async def _monitor_memory(self, interval_seconds: int) -> None:
        """Background memory monitoring task"""
        while self._monitoring_enabled:
            try:
                stats = self.get_memory_stats()
                self._memory_history.append({
                    'timestamp': time.time(),
                    'process_memory_mb': stats.process_memory_mb,
                    'memory_percent': stats.memory_percent
                })
                
                # Check for memory pressure
                if self.is_memory_pressure():
                    logger.warning(f"Memory pressure detected: {stats.process_memory_mb:.1f}MB "
                                 f"({stats.memory_percent:.1f}%)")
                    
                    # Trigger cleanup if we're over emergency threshold
                    if stats.process_memory_mb > self.limits.emergency_cleanup_threshold_mb:
                        self.emergency_cleanup()
                    else:
                        # Regular garbage collection
                        current_memory = stats.process_memory_mb
                        if current_memory - self._last_gc_memory > self.limits.gc_threshold_mb:
                            self.trigger_garbage_collection()
                            self._last_gc_memory = current_memory
                
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in memory monitoring: {e}")
                await asyncio.sleep(interval_seconds)
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory and resource statistics"""
        memory_stats = self.get_memory_stats()
        
        return {
            'memory_stats': {
                'total_memory_mb': memory_stats.total_memory_mb,
                'available_memory_mb': memory_stats.available_memory_mb,
                'used_memory_mb': memory_stats.used_memory_mb,
                'memory_percent': memory_stats.memory_percent,
                'process_memory_mb': memory_stats.process_memory_mb,
                'process_memory_percent': memory_stats.process_memory_percent,
                'swap_memory_mb': memory_stats.swap_memory_mb,
                'large_objects_count': memory_stats.large_objects_count
            },
            'cache_stats': {
                'embedding_cache': self.embedding_cache.get_stats(),
                'chunk_cache': self.chunk_cache.get_stats(),
                'result_cache': self.result_cache.get_stats()
            },
            'object_pools': {
                'numpy_pool': self.numpy_pool.get_stats()
            },
            'gc_stats': memory_stats.gc_collections,
            'limits': {
                'max_memory_mb': self.limits.max_memory_mb,
                'max_memory_percent': self.limits.max_memory_percent,
                'gc_threshold_mb': self.limits.gc_threshold_mb,
                'emergency_cleanup_threshold_mb': self.limits.emergency_cleanup_threshold_mb
            },
            'pressure_indicators': {
                'is_memory_pressure': self.is_memory_pressure(),
                'monitoring_enabled': self._monitoring_enabled,
                'cleanup_callbacks': len(self._cleanup_callbacks)
            }
        }
    
    def create_memory_aware_processor(self, max_batch_size: int = 10):
        """Create a memory-aware batch processor"""
        
        class MemoryAwareBatchProcessor:
            def __init__(self, memory_manager: MemoryManager, max_batch_size: int):
                self.memory_manager = memory_manager
                self.max_batch_size = max_batch_size
                self._processed_count = 0
            
            async def process_batch(self, items: List[Any], 
                                  processor_func: Callable) -> List[Any]:
                """Process items in memory-aware batches"""
                results = []
                
                # Dynamically adjust batch size based on memory
                current_batch_size = self.max_batch_size
                if self.memory_manager.is_memory_pressure():
                    current_batch_size = max(1, current_batch_size // 2)
                
                for i in range(0, len(items), current_batch_size):
                    batch = items[i:i + current_batch_size]
                    
                    # Process batch
                    with self.memory_manager.memory_limit_context(
                        self.memory_manager.limits.max_memory_mb * 0.8
                    ):
                        batch_results = await processor_func(batch)
                        results.extend(batch_results)
                    
                    self._processed_count += len(batch)
                    
                    # Check memory between batches
                    if self.memory_manager.is_memory_pressure():
                        self.memory_manager.trigger_garbage_collection()
                        # Reduce batch size for next iteration
                        current_batch_size = max(1, current_batch_size // 2)
                    
                    # Brief pause to allow memory cleanup
                    await asyncio.sleep(0.1)
                
                return results
        
        return MemoryAwareBatchProcessor(self, max_batch_size)


# Singleton instance
_memory_manager = None


def get_memory_manager() -> MemoryManager:
    """Get the singleton memory manager instance"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


# Memory-aware decorators
def memory_aware(max_memory_mb: Optional[float] = None):
    """Decorator for memory-aware functions"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            memory_manager = get_memory_manager()
            limit = max_memory_mb or memory_manager.limits.max_memory_mb
            
            with memory_manager.memory_limit_context(limit):
                return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            memory_manager = get_memory_manager()
            limit = max_memory_mb or memory_manager.limits.max_memory_mb
            
            with memory_manager.memory_limit_context(limit):
                return func(*args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator