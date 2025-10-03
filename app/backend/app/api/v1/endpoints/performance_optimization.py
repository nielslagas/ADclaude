"""
Performance Optimization API Endpoints
Provides API access to performance optimization features and monitoring
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from app.utils.rag_performance_optimizer import get_performance_optimizer, initialize_performance_optimizer
from app.utils.memory_manager import get_memory_manager
from app.utils.database_optimizer import get_database_optimizer
from app.utils.performance_monitor import get_performance_monitor, initialize_monitoring
from app.tasks.generate_report_tasks.optimized_rag_pipeline import get_optimized_rag_pipeline

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/performance/status")
async def get_performance_status() -> Dict[str, Any]:
    """Get current performance optimization status"""
    try:
        performance_optimizer = get_performance_optimizer()
        memory_manager = get_memory_manager()
        database_optimizer = get_database_optimizer()
        performance_monitor = get_performance_monitor()
        
        return {
            "status": "active",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "performance_optimizer": {
                    "active": True,
                    "stats": performance_optimizer.get_performance_stats()
                },
                "memory_manager": {
                    "active": True,
                    "stats": memory_manager.get_comprehensive_stats()
                },
                "database_optimizer": {
                    "active": True,
                    "stats": await database_optimizer.get_database_stats()
                },
                "performance_monitor": {
                    "active": True,
                    "dashboard_data": performance_monitor.get_metrics_dashboard_data(hours=1)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting performance status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/performance/initialize")
async def initialize_performance_optimization(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Initialize all performance optimization components"""
    try:
        # Initialize components in background
        background_tasks.add_task(initialize_performance_optimizer)
        background_tasks.add_task(initialize_monitoring)
        
        # Warm up optimized pipeline
        optimized_pipeline = get_optimized_rag_pipeline()
        background_tasks.add_task(optimized_pipeline.warm_up_pipeline)
        
        # Start memory monitoring
        memory_manager = get_memory_manager()
        background_tasks.add_task(memory_manager.start_monitoring, 30)
        
        return {
            "message": "Performance optimization initialization started",
            "timestamp": datetime.now().isoformat(),
            "status": "initializing"
        }
        
    except Exception as e:
        logger.error(f"Error initializing performance optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/metrics")
async def get_performance_metrics(hours: int = 1) -> Dict[str, Any]:
    """Get performance metrics for the specified time period"""
    try:
        performance_monitor = get_performance_monitor()
        
        dashboard_data = performance_monitor.get_metrics_dashboard_data(hours=hours)
        
        return {
            "success": True,
            "data": dashboard_data,
            "hours": hours,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/report")
async def get_performance_report(hours: int = 24) -> Dict[str, Any]:
    """Generate comprehensive performance report"""
    try:
        performance_monitor = get_performance_monitor()
        
        report = performance_monitor.get_performance_report(hours=hours)
        
        return {
            "success": True,
            "report": report,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating performance report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/alerts")
async def get_active_alerts() -> Dict[str, Any]:
    """Get active performance alerts"""
    try:
        performance_monitor = get_performance_monitor()
        
        active_alerts = performance_monitor.alert_manager.get_active_alerts()
        
        return {
            "success": True,
            "alerts": [
                {
                    "id": alert.id,
                    "level": alert.level.value,
                    "metric": alert.metric,
                    "message": alert.message,
                    "timestamp": alert.timestamp,
                    "current_value": alert.current_value,
                    "threshold": alert.threshold,
                    "acknowledged": alert.acknowledged
                }
                for alert in active_alerts
            ],
            "count": len(active_alerts),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting active alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/performance/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str) -> Dict[str, Any]:
    """Acknowledge a performance alert"""
    try:
        performance_monitor = get_performance_monitor()
        
        success = performance_monitor.alert_manager.acknowledge_alert(alert_id)
        
        if success:
            return {
                "success": True,
                "message": f"Alert {alert_id} acknowledged",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="Alert not found")
            
    except Exception as e:
        logger.error(f"Error acknowledging alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/performance/cache/clear")
async def clear_performance_caches() -> Dict[str, Any]:
    """Clear all performance-related caches"""
    try:
        performance_optimizer = get_performance_optimizer()
        database_optimizer = get_database_optimizer()
        memory_manager = get_memory_manager()
        
        # Clear caches
        performance_optimizer.clear_all_caches()
        database_optimizer.clear_query_cache()
        memory_manager.embedding_cache.clear()
        memory_manager.chunk_cache.clear()
        memory_manager.result_cache.clear()
        
        return {
            "success": True,
            "message": "All performance caches cleared",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error clearing caches: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/performance/memory/cleanup")
async def trigger_memory_cleanup() -> Dict[str, Any]:
    """Trigger manual memory cleanup"""
    try:
        memory_manager = get_memory_manager()
        
        cleanup_stats = memory_manager.emergency_cleanup()
        
        return {
            "success": True,
            "cleanup_stats": cleanup_stats,
            "message": f"Memory cleanup completed, freed {cleanup_stats['memory_freed_mb']:.2f}MB",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error during memory cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/performance/database/optimize")
async def optimize_database() -> Dict[str, Any]:
    """Optimize database indices and configuration"""
    try:
        database_optimizer = get_database_optimizer()
        
        optimization_results = await database_optimizer.optimize_database_indices()
        
        return {
            "success": True,
            "optimization_results": optimization_results,
            "message": "Database optimization completed",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error optimizing database: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/memory/stats")
async def get_memory_stats() -> Dict[str, Any]:
    """Get detailed memory statistics"""
    try:
        memory_manager = get_memory_manager()
        
        stats = memory_manager.get_comprehensive_stats()
        
        return {
            "success": True,
            "memory_stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/cache/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """Get cache performance statistics"""
    try:
        performance_optimizer = get_performance_optimizer()
        database_optimizer = get_database_optimizer()
        memory_manager = get_memory_manager()
        
        return {
            "success": True,
            "cache_stats": {
                "performance_optimizer": performance_optimizer.cache.get_stats(),
                "database_optimizer": database_optimizer.query_cache.get_stats(),
                "memory_manager": {
                    "embedding_cache": memory_manager.embedding_cache.get_stats(),
                    "chunk_cache": memory_manager.chunk_cache.get_stats(),
                    "result_cache": memory_manager.result_cache.get_stats()
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/performance/config/optimize-for-speed")
async def optimize_for_speed() -> Dict[str, Any]:
    """Optimize system configuration for speed (uses more memory)"""
    try:
        memory_manager = get_memory_manager()
        
        memory_manager.optimize_for_speed()
        
        return {
            "success": True,
            "message": "System optimized for speed",
            "note": "This configuration uses more memory for better performance",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error optimizing for speed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/performance/config/optimize-for-memory")
async def optimize_for_memory() -> Dict[str, Any]:
    """Optimize system configuration for memory efficiency"""
    try:
        memory_manager = get_memory_manager()
        
        memory_manager.optimize_for_large_processing()
        
        return {
            "success": True,
            "message": "System optimized for memory efficiency",
            "note": "This configuration prioritizes memory usage over speed",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error optimizing for memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/export")
async def export_performance_metrics(hours: Optional[int] = 24) -> Dict[str, Any]:
    """Export performance metrics for external analysis"""
    try:
        performance_monitor = get_performance_monitor()
        
        export_data = performance_monitor.export_metrics(hours=hours)
        
        return {
            "success": True,
            "export_data": export_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error exporting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/test")
async def run_performance_test() -> Dict[str, Any]:
    """Run a quick performance test to validate optimizations"""
    try:
        import time
        import asyncio
        
        # Test embedding generation performance
        performance_optimizer = get_performance_optimizer()
        
        test_text = "Test belastbaarheid analyse voor arbeidsdeskundige rapport generatie"
        
        # Test without cache
        performance_optimizer.cache.clear_cache()
        start_time = time.time()
        embedding1 = await performance_optimizer.optimized_embedding_generation(test_text, force_refresh=True)
        uncached_time = time.time() - start_time
        
        # Test with cache
        start_time = time.time()
        embedding2 = await performance_optimizer.optimized_embedding_generation(test_text)
        cached_time = time.time() - start_time
        
        # Calculate improvement
        improvement = ((uncached_time - cached_time) / uncached_time) * 100 if uncached_time > 0 else 0
        
        # Get system stats
        memory_manager = get_memory_manager()
        memory_stats = memory_manager.get_memory_stats()
        
        return {
            "success": True,
            "test_results": {
                "uncached_time": uncached_time,
                "cached_time": cached_time,
                "improvement_percent": improvement,
                "embeddings_match": len(embedding1) == len(embedding2),
                "memory_usage_mb": memory_stats.process_memory_mb
            },
            "message": f"Performance test completed with {improvement:.1f}% improvement",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error running performance test: {e}")
        raise HTTPException(status_code=500, detail=str(e))