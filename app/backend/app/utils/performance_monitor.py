"""
Performance Monitor and Metrics Collection for RAG Pipeline
Comprehensive monitoring system with real-time metrics, alerting, and performance analytics
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from enum import Enum
import threading
import statistics

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: float
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    """Performance alert"""
    id: str
    level: AlertLevel
    metric: str
    message: str
    timestamp: float
    threshold: float
    current_value: float
    acknowledged: bool = False
    resolved: bool = False


@dataclass
class PerformanceSnapshot:
    """Comprehensive performance snapshot"""
    timestamp: float
    query_metrics: Dict[str, Any]
    memory_metrics: Dict[str, Any]
    cache_metrics: Dict[str, Any]
    database_metrics: Dict[str, Any]
    system_metrics: Dict[str, Any]
    alerts: List[Alert]


class MetricCollector:
    """Collects and stores performance metrics"""
    
    def __init__(self, retention_hours: int = 24, max_points_per_metric: int = 1000):
        self.retention_hours = retention_hours
        self.max_points_per_metric = max_points_per_metric
        self._metrics = defaultdict(lambda: deque(maxlen=max_points_per_metric))
        self._lock = threading.RLock()
    
    def add_metric(self, metric_name: str, value: float, 
                   tags: Optional[Dict[str, str]] = None) -> None:
        """Add a metric data point"""
        with self._lock:
            point = MetricPoint(
                timestamp=time.time(),
                value=value,
                tags=tags or {}
            )
            self._metrics[metric_name].append(point)
    
    def get_metric_history(self, metric_name: str, 
                          hours: Optional[int] = None) -> List[MetricPoint]:
        """Get metric history"""
        with self._lock:
            if metric_name not in self._metrics:
                return []
            
            points = list(self._metrics[metric_name])
            
            if hours:
                cutoff_time = time.time() - (hours * 3600)
                points = [p for p in points if p.timestamp >= cutoff_time]
            
            return points
    
    def get_metric_stats(self, metric_name: str, 
                        hours: Optional[int] = None) -> Dict[str, Any]:
        """Get statistical summary of a metric"""
        points = self.get_metric_history(metric_name, hours)
        
        if not points:
            return {
                'count': 0,
                'mean': 0,
                'median': 0,
                'min': 0,
                'max': 0,
                'std_dev': 0
            }
        
        values = [p.value for p in points]
        
        return {
            'count': len(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'min': min(values),
            'max': max(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
            'latest': values[-1],
            'trend': self._calculate_trend(values)
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate metric trend"""
        if len(values) < 5:
            return "stable"
        
        # Simple trend analysis using last 5 vs previous 5 values
        recent = values[-5:]
        previous = values[-10:-5] if len(values) >= 10 else values[:-5]
        
        if not previous:
            return "stable"
        
        recent_avg = statistics.mean(recent)
        previous_avg = statistics.mean(previous)
        
        change_percent = ((recent_avg - previous_avg) / previous_avg) * 100
        
        if change_percent > 10:
            return "increasing"
        elif change_percent < -10:
            return "decreasing"
        else:
            return "stable"
    
    def cleanup_old_metrics(self) -> None:
        """Remove old metric points"""
        cutoff_time = time.time() - (self.retention_hours * 3600)
        
        with self._lock:
            for metric_name in list(self._metrics.keys()):
                points = self._metrics[metric_name]
                # Filter out old points
                filtered_points = deque(
                    (p for p in points if p.timestamp >= cutoff_time),
                    maxlen=self.max_points_per_metric
                )
                self._metrics[metric_name] = filtered_points
                
                # Remove empty metrics
                if not filtered_points:
                    del self._metrics[metric_name]
    
    def get_all_metrics(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all metrics in serializable format"""
        with self._lock:
            result = {}
            for metric_name, points in self._metrics.items():
                result[metric_name] = [
                    {
                        'timestamp': p.timestamp,
                        'value': p.value,
                        'tags': p.tags
                    }
                    for p in points
                ]
            return result


class AlertManager:
    """Manages performance alerts and notifications"""
    
    def __init__(self):
        self._alerts = {}  # Dict[str, Alert]
        self._alert_rules = {}  # Dict[str, AlertRule]
        self._alert_callbacks = []  # List[Callable[[Alert], None]]
        self._lock = threading.RLock()
    
    def add_alert_rule(self, metric_name: str, threshold: float, 
                      comparison: str, level: AlertLevel, 
                      message_template: str) -> None:
        """Add an alert rule"""
        rule = {
            'metric': metric_name,
            'threshold': threshold,
            'comparison': comparison,  # 'gt', 'lt', 'eq'
            'level': level,
            'message_template': message_template
        }
        
        with self._lock:
            self._alert_rules[f"{metric_name}_{comparison}_{threshold}"] = rule
    
    def register_alert_callback(self, callback: Callable[[Alert], None]) -> None:
        """Register callback for alert notifications"""
        self._alert_callbacks.append(callback)
    
    def check_metric_for_alerts(self, metric_name: str, value: float) -> List[Alert]:
        """Check if metric value triggers any alerts"""
        triggered_alerts = []
        
        with self._lock:
            for rule_id, rule in self._alert_rules.items():
                if rule['metric'] != metric_name:
                    continue
                
                # Check if threshold is crossed
                triggered = False
                if rule['comparison'] == 'gt' and value > rule['threshold']:
                    triggered = True
                elif rule['comparison'] == 'lt' and value < rule['threshold']:
                    triggered = True
                elif rule['comparison'] == 'eq' and abs(value - rule['threshold']) < 0.001:
                    triggered = True
                
                if triggered:
                    alert_id = f"{rule_id}_{int(time.time())}"
                    alert = Alert(
                        id=alert_id,
                        level=rule['level'],
                        metric=metric_name,
                        message=rule['message_template'].format(
                            metric=metric_name,
                            value=value,
                            threshold=rule['threshold']
                        ),
                        timestamp=time.time(),
                        threshold=rule['threshold'],
                        current_value=value
                    )
                    
                    self._alerts[alert_id] = alert
                    triggered_alerts.append(alert)
                    
                    # Notify callbacks
                    for callback in self._alert_callbacks:
                        try:
                            callback(alert)
                        except Exception as e:
                            logger.error(f"Alert callback failed: {e}")
        
        return triggered_alerts
    
    def get_active_alerts(self, level: Optional[AlertLevel] = None) -> List[Alert]:
        """Get active (unresolved) alerts"""
        with self._lock:
            alerts = [alert for alert in self._alerts.values() if not alert.resolved]
            
            if level:
                alerts = [alert for alert in alerts if alert.level == level]
            
            return sorted(alerts, key=lambda a: a.timestamp, reverse=True)
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        with self._lock:
            if alert_id in self._alerts:
                self._alerts[alert_id].acknowledged = True
                return True
            return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        with self._lock:
            if alert_id in self._alerts:
                self._alerts[alert_id].resolved = True
                return True
            return False
    
    def cleanup_old_alerts(self, hours: int = 24) -> None:
        """Remove old resolved alerts"""
        cutoff_time = time.time() - (hours * 3600)
        
        with self._lock:
            old_alerts = [
                alert_id for alert_id, alert in self._alerts.items()
                if alert.resolved and alert.timestamp < cutoff_time
            ]
            
            for alert_id in old_alerts:
                del self._alerts[alert_id]


class PerformanceMonitor:
    """Main performance monitoring system"""
    
    def __init__(self):
        self.metric_collector = MetricCollector()
        self.alert_manager = AlertManager()
        self._monitoring_enabled = False
        self._monitoring_task = None
        self._component_monitors = {}
        self._snapshots = deque(maxlen=100)  # Keep last 100 snapshots
        
        # Setup default alert rules
        self._setup_default_alerts()
        
        logger.info("Performance monitor initialized")
    
    def _setup_default_alerts(self) -> None:
        """Setup default performance alert rules"""
        # Memory alerts
        self.alert_manager.add_alert_rule(
            "memory_usage_mb", 1500, "gt", AlertLevel.WARNING,
            "High memory usage: {value:.1f}MB (threshold: {threshold}MB)"
        )
        
        self.alert_manager.add_alert_rule(
            "memory_usage_mb", 2000, "gt", AlertLevel.CRITICAL,
            "Critical memory usage: {value:.1f}MB (threshold: {threshold}MB)"
        )
        
        # Query performance alerts
        self.alert_manager.add_alert_rule(
            "avg_query_time", 5.0, "gt", AlertLevel.WARNING,
            "Slow query performance: {value:.2f}s (threshold: {threshold}s)"
        )
        
        self.alert_manager.add_alert_rule(
            "query_error_rate", 0.1, "gt", AlertLevel.ERROR,
            "High query error rate: {value:.2%} (threshold: {threshold:.2%})"
        )
        
        # Cache performance alerts
        self.alert_manager.add_alert_rule(
            "cache_hit_rate", 0.3, "lt", AlertLevel.WARNING,
            "Low cache hit rate: {value:.2%} (threshold: {threshold:.2%})"
        )
        
        # Database alerts
        self.alert_manager.add_alert_rule(
            "db_connection_errors", 5, "gt", AlertLevel.ERROR,
            "Database connection errors: {value} (threshold: {threshold})"
        )
    
    def add_metric(self, metric_name: str, value: float, 
                   tags: Optional[Dict[str, str]] = None) -> None:
        """Add a metric and check for alerts"""
        self.metric_collector.add_metric(metric_name, value, tags)
        
        # Check for alerts
        alerts = self.alert_manager.check_metric_for_alerts(metric_name, value)
        for alert in alerts:
            logger.log(
                logging.CRITICAL if alert.level == AlertLevel.CRITICAL else logging.WARNING,
                f"ALERT: {alert.message}"
            )
    
    def register_component_monitor(self, name: str, 
                                 monitor_func: Callable[[], Dict[str, Any]]) -> None:
        """Register a component-specific monitoring function"""
        self._component_monitors[name] = monitor_func
    
    async def collect_comprehensive_metrics(self) -> PerformanceSnapshot:
        """Collect metrics from all registered components"""
        timestamp = time.time()
        
        # Collect from all component monitors
        component_metrics = {}
        for name, monitor_func in self._component_monitors.items():
            try:
                metrics = monitor_func()
                component_metrics[name] = metrics
                
                # Extract key metrics for alerting
                if isinstance(metrics, dict):
                    for key, value in metrics.items():
                        if isinstance(value, (int, float)):
                            self.add_metric(f"{name}_{key}", value)
                            
            except Exception as e:
                logger.error(f"Failed to collect metrics from {name}: {e}")
        
        # Create snapshot
        snapshot = PerformanceSnapshot(
            timestamp=timestamp,
            query_metrics=component_metrics.get('query', {}),
            memory_metrics=component_metrics.get('memory', {}),
            cache_metrics=component_metrics.get('cache', {}),
            database_metrics=component_metrics.get('database', {}),
            system_metrics=component_metrics.get('system', {}),
            alerts=self.alert_manager.get_active_alerts()
        )
        
        self._snapshots.append(snapshot)
        return snapshot
    
    async def start_monitoring(self, interval_seconds: int = 60) -> None:
        """Start background performance monitoring"""
        if self._monitoring_enabled:
            return
        
        self._monitoring_enabled = True
        self._monitoring_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )
        logger.info(f"Performance monitoring started (interval: {interval_seconds}s)")
    
    async def stop_monitoring(self) -> None:
        """Stop background monitoring"""
        self._monitoring_enabled = False
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
        logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self, interval_seconds: int) -> None:
        """Main monitoring loop"""
        while self._monitoring_enabled:
            try:
                # Collect comprehensive metrics
                snapshot = await self.collect_comprehensive_metrics()
                
                # Cleanup old data
                self.metric_collector.cleanup_old_metrics()
                self.alert_manager.cleanup_old_alerts()
                
                # Log summary every 5 minutes
                if int(time.time()) % 300 == 0:
                    await self._log_performance_summary(snapshot)
                
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval_seconds)
    
    async def _log_performance_summary(self, snapshot: PerformanceSnapshot) -> None:
        """Log performance summary"""
        summary_lines = [
            "=== Performance Summary ===",
            f"Timestamp: {datetime.fromtimestamp(snapshot.timestamp)}",
        ]
        
        # Active alerts
        if snapshot.alerts:
            summary_lines.append(f"Active Alerts: {len(snapshot.alerts)}")
            for alert in snapshot.alerts[:3]:  # Show top 3
                summary_lines.append(f"  - {alert.level.value.upper()}: {alert.message}")
        
        # Key metrics
        for component, metrics in [
            ("Query", snapshot.query_metrics),
            ("Memory", snapshot.memory_metrics),
            ("Cache", snapshot.cache_metrics),
            ("Database", snapshot.database_metrics)
        ]:
            if metrics:
                summary_lines.append(f"{component} Metrics:")
                for key, value in metrics.items():
                    if isinstance(value, (int, float)):
                        if 'time' in key.lower() or 'duration' in key.lower():
                            summary_lines.append(f"  {key}: {value:.3f}s")
                        elif 'rate' in key.lower() or 'percent' in key.lower():
                            summary_lines.append(f"  {key}: {value:.1%}")
                        elif 'mb' in key.lower():
                            summary_lines.append(f"  {key}: {value:.1f}MB")
                        else:
                            summary_lines.append(f"  {key}: {value}")
        
        summary_lines.append("=" * 30)
        logger.info("\n".join(summary_lines))
    
    def get_metrics_dashboard_data(self, hours: int = 1) -> Dict[str, Any]:
        """Get dashboard data for the last N hours"""
        # Get key metrics with statistics
        key_metrics = [
            'memory_usage_mb', 'avg_query_time', 'cache_hit_rate',
            'query_count', 'error_count', 'db_connections'
        ]
        
        dashboard_data = {
            'timestamp': time.time(),
            'time_range_hours': hours,
            'metrics': {},
            'alerts': {
                'critical': len([a for a in self.alert_manager.get_active_alerts() if a.level == AlertLevel.CRITICAL]),
                'error': len([a for a in self.alert_manager.get_active_alerts() if a.level == AlertLevel.ERROR]),
                'warning': len([a for a in self.alert_manager.get_active_alerts() if a.level == AlertLevel.WARNING]),
                'recent_alerts': [asdict(a) for a in self.alert_manager.get_active_alerts()[:10]]
            },
            'performance_trends': {}
        }
        
        # Get metric statistics
        for metric_name in key_metrics:
            stats = self.metric_collector.get_metric_stats(metric_name, hours)
            if stats['count'] > 0:
                dashboard_data['metrics'][metric_name] = stats
                dashboard_data['performance_trends'][metric_name] = stats['trend']
        
        # Get recent snapshots
        recent_snapshots = [
            asdict(snapshot) for snapshot in list(self._snapshots)[-10:]
        ]
        dashboard_data['recent_snapshots'] = recent_snapshots
        
        return dashboard_data
    
    def export_metrics(self, hours: Optional[int] = None) -> Dict[str, Any]:
        """Export all metrics for external analysis"""
        return {
            'export_timestamp': time.time(),
            'time_range_hours': hours or self.metric_collector.retention_hours,
            'metrics': self.metric_collector.get_all_metrics(),
            'active_alerts': [asdict(a) for a in self.alert_manager.get_active_alerts()],
            'performance_snapshots': [asdict(s) for s in self._snapshots]
        }
    
    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate a comprehensive performance report"""
        report_start_time = time.time() - (hours * 3600)
        
        # Get all metrics for the time period
        all_metrics = {}
        for metric_name in ['memory_usage_mb', 'avg_query_time', 'cache_hit_rate', 
                           'query_count', 'error_count']:
            stats = self.metric_collector.get_metric_stats(metric_name, hours)
            if stats['count'] > 0:
                all_metrics[metric_name] = stats
        
        # Analyze alerts
        alert_summary = {
            'total_alerts': len(self.alert_manager._alerts),
            'active_alerts': len(self.alert_manager.get_active_alerts()),
            'by_level': {
                level.value: len([a for a in self.alert_manager.get_active_alerts() if a.level == level])
                for level in AlertLevel
            }
        }
        
        # Calculate performance score (0-100)
        score_factors = {
            'memory_efficiency': 100 - min(all_metrics.get('memory_usage_mb', {}).get('mean', 0) / 20, 100),
            'query_performance': max(0, 100 - (all_metrics.get('avg_query_time', {}).get('mean', 0) * 20)),
            'cache_effectiveness': all_metrics.get('cache_hit_rate', {}).get('mean', 0) * 100,
            'error_rate': max(0, 100 - (all_metrics.get('error_count', {}).get('mean', 0) * 10)),
            'alert_impact': max(0, 100 - (alert_summary['active_alerts'] * 10))
        }
        
        overall_score = sum(score_factors.values()) / len(score_factors)
        
        return {
            'report_timestamp': time.time(),
            'time_period_hours': hours,
            'overall_performance_score': round(overall_score, 1),
            'score_breakdown': score_factors,
            'metrics_summary': all_metrics,
            'alert_summary': alert_summary,
            'recommendations': self._generate_recommendations(all_metrics, alert_summary)
        }
    
    def _generate_recommendations(self, metrics: Dict[str, Any], 
                                alert_summary: Dict[str, Any]) -> List[str]:
        """Generate performance improvement recommendations"""
        recommendations = []
        
        # Memory recommendations
        memory_stats = metrics.get('memory_usage_mb', {})
        if memory_stats.get('mean', 0) > 1000:
            recommendations.append("Consider increasing memory limits or optimizing memory usage")
        
        # Query performance recommendations
        query_stats = metrics.get('avg_query_time', {})
        if query_stats.get('mean', 0) > 2.0:
            recommendations.append("Query performance is slow - consider database optimization")
        
        # Cache recommendations
        cache_stats = metrics.get('cache_hit_rate', {})
        if cache_stats.get('mean', 0) < 0.5:
            recommendations.append("Low cache hit rate - consider increasing cache sizes")
        
        # Alert recommendations
        if alert_summary['active_alerts'] > 5:
            recommendations.append("High number of active alerts - investigate root causes")
        
        return recommendations


# Singleton instance
_performance_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the singleton performance monitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


async def initialize_monitoring():
    """Initialize monitoring with component integrations"""
    monitor = get_performance_monitor()
    
    # Register component monitors
    try:
        from app.utils.memory_manager import get_memory_manager
        memory_manager = get_memory_manager()
        monitor.register_component_monitor(
            "memory", 
            lambda: memory_manager.get_comprehensive_stats()
        )
    except Exception as e:
        logger.warning(f"Failed to register memory monitor: {e}")
    
    try:
        from app.utils.rag_performance_optimizer import get_performance_optimizer
        optimizer = get_performance_optimizer()
        monitor.register_component_monitor(
            "rag_performance", 
            lambda: optimizer.get_performance_stats()
        )
    except Exception as e:
        logger.warning(f"Failed to register RAG performance monitor: {e}")
    
    try:
        from app.utils.database_optimizer import get_database_optimizer
        db_optimizer = get_database_optimizer()
        monitor.register_component_monitor(
            "database", 
            lambda: asyncio.run(db_optimizer.get_database_stats())
        )
    except Exception as e:
        logger.warning(f"Failed to register database monitor: {e}")
    
    # Start monitoring
    await monitor.start_monitoring(interval_seconds=30)
    
    logger.info("Performance monitoring initialized with component integrations")