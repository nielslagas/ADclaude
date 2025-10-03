"""
RAG Pipeline Monitoring en Metrics voor AI-Arbeidsdeskundige
Real-time performance tracking, analytics en quality metrics
"""

import logging
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import json
import statistics
from collections import defaultdict, deque

from app.utils.smart_document_classifier import DocumentType
from app.utils.context_aware_prompts import ReportSection, ComplexityLevel
from app.utils.quality_controller import QualitySeverity


class MetricType(Enum):
    """Types van metrics die we tracken"""
    PROCESSING_TIME = "processing_time"
    QUALITY_SCORE = "quality_score"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    MEMORY_USAGE = "memory_usage"
    TOKEN_USAGE = "token_usage"
    USER_SATISFACTION = "user_satisfaction"
    CACHE_HIT_RATE = "cache_hit_rate"


class ComponentType(Enum):
    """RAG pipeline componenten"""
    DOCUMENT_CLASSIFIER = "document_classifier"
    RAG_PIPELINE = "rag_pipeline"
    PROMPT_GENERATOR = "prompt_generator"
    QUALITY_CONTROLLER = "quality_controller"
    MULTIMODAL_RAG = "multimodal_rag"
    VECTOR_STORE = "vector_store"
    LLM_PROVIDER = "llm_provider"
    AUDIO_TRANSCRIBER = "audio_transcriber"


class AlertLevel(Enum):
    """Alert niveaus voor monitoring"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricData:
    """Basis metric data structure"""
    timestamp: datetime
    component: ComponentType
    metric_type: MetricType
    value: float
    metadata: Dict[str, Any]
    tags: Dict[str, str]


@dataclass
class PerformanceSnapshot:
    """Performance snapshot op een moment"""
    timestamp: datetime
    processing_times: Dict[ComponentType, float]
    quality_scores: Dict[str, float]
    error_counts: Dict[ComponentType, int]
    throughput: float
    active_requests: int
    memory_usage_mb: float
    token_usage: Dict[str, int]


@dataclass
class QualityMetrics:
    """Kwaliteitsmetrics voor content generatie"""
    overall_score: float
    section_scores: Dict[ReportSection, float]
    issue_distribution: Dict[QualitySeverity, int]
    improvement_rate: float
    user_acceptance_rate: float


@dataclass
class Alert:
    """Monitoring alert"""
    timestamp: datetime
    level: AlertLevel
    component: ComponentType
    message: str
    value: float
    threshold: float
    metadata: Dict[str, Any]


class MetricsCollector:
    """Centralized metrics collection system"""
    
    def __init__(self, max_history_size: int = 10000):
        self.logger = logging.getLogger(__name__)
        self.max_history_size = max_history_size
        
        # In-memory storage (in productie zou dit een database zijn)
        self.metrics_history = deque(maxlen=max_history_size)
        self.performance_snapshots = deque(maxlen=1000)
        self.alerts = deque(maxlen=1000)
        
        # Real-time counters
        self.request_counts = defaultdict(int)
        self.error_counts = defaultdict(int)
        self.processing_times = defaultdict(list)
        self.quality_scores = defaultdict(list)
        
        # Configuration
        self.alert_thresholds = self._load_alert_thresholds()
        self.monitoring_config = self._load_monitoring_config()
        
        # Active tracking
        self.active_requests = {}
        self.component_stats = defaultdict(dict)
    
    def _load_alert_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Laad alert drempels per component en metric"""
        return {
            ComponentType.DOCUMENT_CLASSIFIER.value: {
                MetricType.PROCESSING_TIME.value: 5.0,  # 5 seconden
                MetricType.ERROR_RATE.value: 0.05,      # 5% error rate
                MetricType.QUALITY_SCORE.value: 0.7     # Minimum kwaliteit
            },
            ComponentType.RAG_PIPELINE.value: {
                MetricType.PROCESSING_TIME.value: 10.0,
                MetricType.ERROR_RATE.value: 0.03,
                MetricType.QUALITY_SCORE.value: 0.75
            },
            ComponentType.PROMPT_GENERATOR.value: {
                MetricType.PROCESSING_TIME.value: 3.0,
                MetricType.ERROR_RATE.value: 0.02,
                MetricType.QUALITY_SCORE.value: 0.8
            },
            ComponentType.QUALITY_CONTROLLER.value: {
                MetricType.PROCESSING_TIME.value: 8.0,
                MetricType.ERROR_RATE.value: 0.02,
                MetricType.QUALITY_SCORE.value: 0.85
            },
            ComponentType.MULTIMODAL_RAG.value: {
                MetricType.PROCESSING_TIME.value: 15.0,
                MetricType.ERROR_RATE.value: 0.05,
                MetricType.QUALITY_SCORE.value: 0.7
            },
            ComponentType.LLM_PROVIDER.value: {
                MetricType.PROCESSING_TIME.value: 12.0,
                MetricType.ERROR_RATE.value: 0.01,
                MetricType.TOKEN_USAGE.value: 100000  # Max tokens per hour
            }
        }
    
    def _load_monitoring_config(self) -> Dict[str, Any]:
        """Laad monitoring configuratie"""
        return {
            "snapshot_interval_seconds": 60,
            "metric_retention_hours": 24,
            "alert_cooldown_minutes": 15,
            "batch_size": 100,
            "enable_real_time_alerts": True,
            "enable_performance_profiling": True
        }
    
    def record_metric(
        self,
        component: ComponentType,
        metric_type: MetricType,
        value: float,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None
    ):
        """Record een individual metric"""
        
        metric = MetricData(
            timestamp=datetime.utcnow(),
            component=component,
            metric_type=metric_type,
            value=value,
            metadata=metadata or {},
            tags=tags or {}
        )
        
        self.metrics_history.append(metric)
        
        # Update real-time counters
        if metric_type == MetricType.PROCESSING_TIME:
            self.processing_times[component].append(value)
            # Keep only recent values
            if len(self.processing_times[component]) > 100:
                self.processing_times[component] = self.processing_times[component][-100:]
        
        elif metric_type == MetricType.QUALITY_SCORE:
            self.quality_scores[component].append(value)
            if len(self.quality_scores[component]) > 100:
                self.quality_scores[component] = self.quality_scores[component][-100:]
        
        # Check for alerts
        self._check_alert_conditions(metric)
        
        self.logger.debug(f"Recorded metric: {component.value}.{metric_type.value} = {value}")
    
    def start_request(self, request_id: str, component: ComponentType, metadata: Dict[str, Any] = None):
        """Start tracking een request"""
        self.active_requests[request_id] = {
            "component": component,
            "start_time": time.time(),
            "metadata": metadata or {}
        }
        self.request_counts[component] += 1
    
    def end_request(self, request_id: str, success: bool = True, metadata: Dict[str, Any] = None):
        """Beëindig tracking van een request"""
        if request_id not in self.active_requests:
            self.logger.warning(f"Request {request_id} not found in active requests")
            return
        
        request_info = self.active_requests.pop(request_id)
        component = request_info["component"]
        processing_time = time.time() - request_info["start_time"]
        
        # Record processing time
        self.record_metric(
            component=component,
            metric_type=MetricType.PROCESSING_TIME,
            value=processing_time,
            metadata={
                **request_info["metadata"],
                **(metadata or {}),
                "success": success
            }
        )
        
        # Record error if applicable
        if not success:
            self.error_counts[component] += 1
            self.record_metric(
                component=component,
                metric_type=MetricType.ERROR_RATE,
                value=1.0,
                metadata=metadata
            )
    
    def record_quality_metrics(
        self,
        component: ComponentType,
        overall_score: float,
        section_scores: Optional[Dict[ReportSection, float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record kwaliteitsmetrics"""
        
        self.record_metric(
            component=component,
            metric_type=MetricType.QUALITY_SCORE,
            value=overall_score,
            metadata={
                **(metadata or {}),
                "section_scores": {k.value: v for k, v in (section_scores or {}).items()}
            }
        )
    
    def record_token_usage(
        self,
        component: ComponentType,
        input_tokens: int,
        output_tokens: int,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record token usage voor LLM calls"""
        
        total_tokens = input_tokens + output_tokens
        
        self.record_metric(
            component=component,
            metric_type=MetricType.TOKEN_USAGE,
            value=total_tokens,
            metadata={
                **(metadata or {}),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens
            }
        )
    
    def _check_alert_conditions(self, metric: MetricData):
        """Check of een metric een alert moet triggeren"""
        
        if not self.monitoring_config["enable_real_time_alerts"]:
            return
        
        component_key = metric.component.value
        metric_key = metric.metric_type.value
        
        thresholds = self.alert_thresholds.get(component_key, {})
        threshold = thresholds.get(metric_key)
        
        if threshold is None:
            return
        
        # Check threshold violation
        alert_triggered = False
        alert_level = AlertLevel.INFO
        
        if metric.metric_type == MetricType.PROCESSING_TIME and metric.value > threshold:
            alert_triggered = True
            alert_level = AlertLevel.WARNING if metric.value < threshold * 2 else AlertLevel.ERROR
        
        elif metric.metric_type == MetricType.ERROR_RATE and metric.value > threshold:
            alert_triggered = True
            alert_level = AlertLevel.ERROR
        
        elif metric.metric_type == MetricType.QUALITY_SCORE and metric.value < threshold:
            alert_triggered = True
            alert_level = AlertLevel.WARNING if metric.value > threshold * 0.8 else AlertLevel.ERROR
        
        elif metric.metric_type == MetricType.TOKEN_USAGE and metric.value > threshold:
            alert_triggered = True
            alert_level = AlertLevel.WARNING
        
        if alert_triggered:
            self._create_alert(
                level=alert_level,
                component=metric.component,
                message=f"{metric.metric_type.value} threshold exceeded",
                value=metric.value,
                threshold=threshold,
                metadata=metric.metadata
            )
    
    def _create_alert(
        self,
        level: AlertLevel,
        component: ComponentType,
        message: str,
        value: float,
        threshold: float,
        metadata: Dict[str, Any]
    ):
        """Creëer een nieuwe alert"""
        
        alert = Alert(
            timestamp=datetime.utcnow(),
            level=level,
            component=component,
            message=message,
            value=value,
            threshold=threshold,
            metadata=metadata
        )
        
        self.alerts.append(alert)
        
        # Log alert
        log_level = logging.WARNING if level in [AlertLevel.WARNING, AlertLevel.ERROR] else logging.INFO
        if level == AlertLevel.CRITICAL:
            log_level = logging.CRITICAL
        
        self.logger.log(
            log_level,
            f"ALERT [{level.value.upper()}] {component.value}: {message} "
            f"(value: {value}, threshold: {threshold})"
        )
    
    def take_performance_snapshot(self) -> PerformanceSnapshot:
        """Neem een performance snapshot"""
        
        current_time = datetime.utcnow()
        
        # Calculate average processing times per component
        processing_times = {}
        for component, times in self.processing_times.items():
            if times:
                processing_times[component] = statistics.mean(times[-10:])  # Last 10 measurements
        
        # Calculate quality scores
        quality_scores = {}
        for component, scores in self.quality_scores.items():
            if scores:
                quality_scores[component.value] = statistics.mean(scores[-10:])
        
        # Calculate error counts (recent)
        recent_errors = {}
        cutoff_time = current_time - timedelta(minutes=5)
        
        for metric in reversed(self.metrics_history):
            if metric.timestamp < cutoff_time:
                break
            if metric.metric_type == MetricType.ERROR_RATE:
                component = metric.component
                recent_errors[component] = recent_errors.get(component, 0) + 1
        
        # Calculate throughput (requests per minute)
        recent_requests = sum(1 for metric in self.metrics_history 
                            if metric.timestamp > cutoff_time)
        throughput = recent_requests / 5.0  # per minute
        
        # Get memory usage (simplified - in productie zou dit systeemmetrics zijn)
        memory_usage = len(self.metrics_history) * 0.1  # Rough estimate in MB
        
        # Token usage
        token_usage = {"total": 0, "input": 0, "output": 0}
        for metric in self.metrics_history:
            if (metric.metric_type == MetricType.TOKEN_USAGE and 
                metric.timestamp > cutoff_time):
                token_usage["total"] += int(metric.value)
                token_usage["input"] += metric.metadata.get("input_tokens", 0)
                token_usage["output"] += metric.metadata.get("output_tokens", 0)
        
        snapshot = PerformanceSnapshot(
            timestamp=current_time,
            processing_times=processing_times,
            quality_scores=quality_scores,
            error_counts=recent_errors,
            throughput=throughput,
            active_requests=len(self.active_requests),
            memory_usage_mb=memory_usage,
            token_usage=token_usage
        )
        
        self.performance_snapshots.append(snapshot)
        return snapshot
    
    def get_component_statistics(self, component: ComponentType, hours: int = 1) -> Dict[str, Any]:
        """Krijg statistieken voor een specifiek component"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        component_metrics = [
            metric for metric in self.metrics_history
            if metric.component == component and metric.timestamp > cutoff_time
        ]
        
        if not component_metrics:
            return {"error": "No data available for this component"}
        
        # Group by metric type
        metrics_by_type = defaultdict(list)
        for metric in component_metrics:
            metrics_by_type[metric.metric_type].append(metric.value)
        
        statistics_data = {}
        for metric_type, values in metrics_by_type.items():
            if values:
                statistics_data[metric_type.value] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0
                }
        
        return {
            "component": component.value,
            "time_range_hours": hours,
            "total_metrics": len(component_metrics),
            "statistics": statistics_data,
            "recent_errors": self.error_counts.get(component, 0),
            "request_count": self.request_counts.get(component, 0)
        }
    
    def get_recent_alerts(self, hours: int = 1, level: Optional[AlertLevel] = None) -> List[Dict[str, Any]]:
        """Krijg recente alerts"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_alerts = [
            alert for alert in self.alerts
            if alert.timestamp > cutoff_time
        ]
        
        if level:
            recent_alerts = [alert for alert in recent_alerts if alert.level == level]
        
        return [
            {
                "timestamp": alert.timestamp.isoformat(),
                "level": alert.level.value,
                "component": alert.component.value,
                "message": alert.message,
                "value": alert.value,
                "threshold": alert.threshold,
                "metadata": alert.metadata
            }
            for alert in sorted(recent_alerts, key=lambda x: x.timestamp, reverse=True)
        ]
    
    def get_quality_dashboard_data(self, hours: int = 24) -> Dict[str, Any]:
        """Krijg data voor quality dashboard"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        quality_metrics = [
            metric for metric in self.metrics_history
            if (metric.metric_type == MetricType.QUALITY_SCORE and 
                metric.timestamp > cutoff_time)
        ]
        
        if not quality_metrics:
            return {"error": "No quality data available"}
        
        # Overall quality trend
        quality_scores = [metric.value for metric in quality_metrics]
        quality_trend = {
            "current_average": statistics.mean(quality_scores[-10:]) if len(quality_scores) >= 10 else statistics.mean(quality_scores),
            "overall_average": statistics.mean(quality_scores),
            "min_score": min(quality_scores),
            "max_score": max(quality_scores),
            "total_evaluations": len(quality_scores)
        }
        
        # Quality by component
        quality_by_component = defaultdict(list)
        for metric in quality_metrics:
            quality_by_component[metric.component].append(metric.value)
        
        component_quality = {}
        for component, scores in quality_by_component.items():
            component_quality[component.value] = {
                "average": statistics.mean(scores),
                "count": len(scores),
                "trend": "improving" if len(scores) > 5 and statistics.mean(scores[-5:]) > statistics.mean(scores[:-5]) else "stable"
            }
        
        # Section quality (from metadata)
        section_scores = defaultdict(list)
        for metric in quality_metrics:
            section_data = metric.metadata.get("section_scores", {})
            for section, score in section_data.items():
                section_scores[section].append(score)
        
        section_quality = {}
        for section, scores in section_scores.items():
            if scores:
                section_quality[section] = {
                    "average": statistics.mean(scores),
                    "count": len(scores)
                }
        
        return {
            "time_range_hours": hours,
            "quality_trend": quality_trend,
            "component_quality": component_quality,
            "section_quality": section_quality,
            "recent_snapshots": [
                {
                    "timestamp": snapshot.timestamp.isoformat(),
                    "quality_scores": snapshot.quality_scores
                }
                for snapshot in list(self.performance_snapshots)[-24:]  # Last 24 snapshots
            ]
        }
    
    def export_metrics(self, hours: int = 1, format: str = "json") -> str:
        """Export metrics voor externe analyse"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        export_metrics = [
            metric for metric in self.metrics_history
            if metric.timestamp > cutoff_time
        ]
        
        if format == "json":
            export_data = {
                "export_timestamp": datetime.utcnow().isoformat(),
                "time_range_hours": hours,
                "total_metrics": len(export_metrics),
                "metrics": [
                    {
                        "timestamp": metric.timestamp.isoformat(),
                        "component": metric.component.value,
                        "metric_type": metric.metric_type.value,
                        "value": metric.value,
                        "metadata": metric.metadata,
                        "tags": metric.tags
                    }
                    for metric in export_metrics
                ]
            }
            return json.dumps(export_data, indent=2)
        
        elif format == "prometheus":
            return self._export_prometheus_format(export_metrics)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_prometheus_format(self, metrics: List[MetricData]) -> str:
        """Export metrics in Prometheus exposition format"""
        
        # Group metrics by type and component
        metric_groups = defaultdict(lambda: defaultdict(list))
        for metric in metrics:
            metric_groups[metric.metric_type][metric.component].append(metric)
        
        prometheus_lines = []
        
        # Header
        prometheus_lines.append("# AI-Arbeidsdeskundige RAG Pipeline Metrics")
        prometheus_lines.append(f"# Generated at {datetime.utcnow().isoformat()}")
        prometheus_lines.append("")
        
        for metric_type, components in metric_groups.items():
            metric_name = f"ai_arbeidsdeskundige_{metric_type.value}"
            
            # HELP line
            help_text = self._get_prometheus_help_text(metric_type)
            prometheus_lines.append(f"# HELP {metric_name} {help_text}")
            
            # TYPE line
            prometheus_type = self._get_prometheus_type(metric_type)
            prometheus_lines.append(f"# TYPE {metric_name} {prometheus_type}")
            
            for component, component_metrics in components.items():
                if not component_metrics:
                    continue
                
                # Use latest value for gauge metrics, sum for counters
                if prometheus_type == "gauge":
                    latest_metric = max(component_metrics, key=lambda m: m.timestamp)
                    value = latest_metric.value
                else:  # counter
                    value = sum(m.value for m in component_metrics)
                
                labels = f"component=\"{component.value}\""
                prometheus_lines.append(f"{metric_name}{{{labels}}} {value}")
            
            prometheus_lines.append("")
        
        # Add system health score
        health_score = self._calculate_system_health()
        prometheus_lines.append("# HELP ai_arbeidsdeskundige_system_health Overall system health score (0-1)")
        prometheus_lines.append("# TYPE ai_arbeidsdeskundige_system_health gauge")
        prometheus_lines.append(f"ai_arbeidsdeskundige_system_health {health_score}")
        
        return "\n".join(prometheus_lines)
    
    def _get_prometheus_help_text(self, metric_type: MetricType) -> str:
        """Get help text for Prometheus metrics"""
        help_texts = {
            MetricType.PROCESSING_TIME: "Time taken to process requests in seconds",
            MetricType.QUALITY_SCORE: "Quality score of generated content (0-1)",
            MetricType.ERROR_RATE: "Number of errors encountered",
            MetricType.THROUGHPUT: "Requests processed per minute",
            MetricType.MEMORY_USAGE: "Memory usage in MB",
            MetricType.TOKEN_USAGE: "Number of tokens consumed",
            MetricType.USER_SATISFACTION: "User satisfaction rating (0-1)",
            MetricType.CACHE_HIT_RATE: "Cache hit rate percentage (0-1)"
        }
        return help_texts.get(metric_type, "System metric")
    
    def _get_prometheus_type(self, metric_type: MetricType) -> str:
        """Get Prometheus metric type"""
        gauge_metrics = {
            MetricType.PROCESSING_TIME,
            MetricType.QUALITY_SCORE,
            MetricType.MEMORY_USAGE,
            MetricType.USER_SATISFACTION,
            MetricType.CACHE_HIT_RATE
        }
        return "gauge" if metric_type in gauge_metrics else "counter"
    
    def _calculate_system_health(self) -> float:
        """Calculate overall system health score"""
        health_factors = []
        
        # Processing time health
        if self.processing_times:
            avg_times = []
            for component, times in self.processing_times.items():
                if times:
                    avg_times.append(statistics.mean(times[-10:]))
            
            if avg_times:
                avg_time = statistics.mean(avg_times)
                # Good if under 5s, poor if over 15s
                time_health = max(0, min(1, (15 - avg_time) / 10))
                health_factors.append(time_health)
        
        # Error rate health
        total_errors = sum(self.error_counts.values())
        error_health = max(0, min(1, (10 - total_errors) / 10))
        health_factors.append(error_health)
        
        # Quality health
        if self.quality_scores:
            quality_values = []
            for component, scores in self.quality_scores.items():
                if scores:
                    quality_values.extend(scores[-5:])
            
            if quality_values:
                avg_quality = statistics.mean(quality_values)
                health_factors.append(avg_quality)
        
        return statistics.mean(health_factors) if health_factors else 0.5
    
    def export_prometheus_metrics(self) -> str:
        """Export current metrics in Prometheus format"""
        return self.export_metrics(hours=1, format="prometheus")
    
    def get_rag_health_status(self) -> Dict[str, Any]:
        """Get comprehensive RAG pipeline health status"""
        health_score = self._calculate_system_health()
        
        # Determine status based on health score
        if health_score >= 0.8:
            status = "healthy"
            message = "All RAG components operating normally"
        elif health_score >= 0.6:
            status = "warning"
            message = "Some RAG components showing degraded performance"
        elif health_score >= 0.4:
            status = "degraded"
            message = "RAG pipeline experiencing significant issues"
        else:
            status = "critical"
            message = "RAG pipeline requires immediate attention"
        
        # Component-specific health
        component_health = {}
        for component in ComponentType:
            component_errors = self.error_counts.get(component, 0)
            component_times = self.processing_times.get(component, [])
            avg_time = statistics.mean(component_times[-5:]) if component_times else 0
            
            if component_errors > 5:
                component_health[component.value] = "unhealthy"
            elif avg_time > 10:
                component_health[component.value] = "slow"
            else:
                component_health[component.value] = "healthy"
        
        # Recent critical alerts
        critical_alerts = [
            alert for alert in self.alerts
            if (alert.level == AlertLevel.CRITICAL and 
                alert.timestamp > datetime.utcnow() - timedelta(minutes=10))
        ]
        
        return {
            "status": status,
            "message": message,
            "health_score": round(health_score, 3),
            "timestamp": datetime.utcnow().isoformat(),
            "components": component_health,
            "active_requests": len(self.active_requests),
            "critical_alerts": len(critical_alerts),
            "uptime_seconds": (datetime.utcnow() - datetime(2024, 1, 1)).total_seconds()
        }
    
    def get_performance_profile(
        self, 
        component: Optional[ComponentType] = None, 
        duration_minutes: int = 5
    ) -> Dict[str, Any]:
        """Get detailed performance profile for analysis"""
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=duration_minutes)
        
        # Filter metrics by component if specified
        relevant_metrics = [
            metric for metric in self.metrics_history
            if (metric.timestamp > cutoff_time and 
                (component is None or metric.component == component))
        ]
        
        profile_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "duration_minutes": duration_minutes,
            "component_filter": component.value if component else "all",
            "total_metrics": len(relevant_metrics)
        }
        
        # Performance breakdown by component
        component_performance = defaultdict(lambda: {
            "request_count": 0,
            "avg_processing_time": 0,
            "error_count": 0,
            "quality_scores": [],
            "token_usage": {"total": 0, "input": 0, "output": 0}
        })
        
        for metric in relevant_metrics:
            comp = metric.component.value
            comp_data = component_performance[comp]
            
            if metric.metric_type == MetricType.PROCESSING_TIME:
                comp_data["request_count"] += 1
                current_avg = comp_data["avg_processing_time"]
                count = comp_data["request_count"]
                comp_data["avg_processing_time"] = (
                    (current_avg * (count - 1) + metric.value) / count
                )
            
            elif metric.metric_type == MetricType.ERROR_RATE:
                comp_data["error_count"] += 1
            
            elif metric.metric_type == MetricType.QUALITY_SCORE:
                comp_data["quality_scores"].append(metric.value)
            
            elif metric.metric_type == MetricType.TOKEN_USAGE:
                comp_data["token_usage"]["total"] += int(metric.value)
                comp_data["token_usage"]["input"] += metric.metadata.get("input_tokens", 0)
                comp_data["token_usage"]["output"] += metric.metadata.get("output_tokens", 0)
        
        # Calculate summary statistics
        for comp, data in component_performance.items():
            if data["quality_scores"]:
                data["avg_quality_score"] = statistics.mean(data["quality_scores"])
                data["quality_std_dev"] = statistics.stdev(data["quality_scores"]) if len(data["quality_scores"]) > 1 else 0
            else:
                data["avg_quality_score"] = None
                data["quality_std_dev"] = None
            
            # Clean up raw quality scores for response
            del data["quality_scores"]
        
        profile_data["component_performance"] = dict(component_performance)
        
        # System-wide statistics
        all_processing_times = [
            m.value for m in relevant_metrics 
            if m.metric_type == MetricType.PROCESSING_TIME
        ]
        
        profile_data["system_statistics"] = {
            "total_requests": len(all_processing_times),
            "avg_processing_time": statistics.mean(all_processing_times) if all_processing_times else 0,
            "median_processing_time": statistics.median(all_processing_times) if all_processing_times else 0,
            "p95_processing_time": self._calculate_percentile(all_processing_times, 95) if all_processing_times else 0,
            "p99_processing_time": self._calculate_percentile(all_processing_times, 99) if all_processing_times else 0,
            "total_errors": len([m for m in relevant_metrics if m.metric_type == MetricType.ERROR_RATE])
        }
        
        # Resource utilization estimate
        profile_data["resource_utilization"] = {
            "memory_usage_mb": len(self.metrics_history) * 0.1,  # Rough estimate
            "active_requests": len(self.active_requests),
            "cache_efficiency": self._calculate_cache_efficiency()
        }
        
        return profile_data
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile for performance metrics"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * percentile / 100
        f = int(k)
        c = k - f
        
        if f + 1 < len(sorted_values):
            return sorted_values[f] * (1 - c) + sorted_values[f + 1] * c
        else:
            return sorted_values[f]
    
    def _calculate_cache_efficiency(self) -> float:
        """Calculate cache hit rate efficiency"""
        cache_metrics = [
            m for m in self.metrics_history
            if m.metric_type == MetricType.CACHE_HIT_RATE
        ]
        
        if not cache_metrics:
            return 0.0
        
        recent_cache_metrics = cache_metrics[-10:]  # Last 10 measurements
        return statistics.mean([m.value for m in recent_cache_metrics])
    
    def reset_metrics(self):
        """Reset alle metrics (voor testing)"""
        self.metrics_history.clear()
        self.performance_snapshots.clear()
        self.alerts.clear()
        self.request_counts.clear()
        self.error_counts.clear()
        self.processing_times.clear()
        self.quality_scores.clear()
        self.active_requests.clear()
        self.component_stats.clear()


# Global metrics collector instance
metrics_collector = MetricsCollector()


# Decorators voor automatische metrics collection
def monitor_performance(component: ComponentType):
    """Decorator voor automatische performance monitoring"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            request_id = f"{component.value}_{int(time.time() * 1000)}"
            metrics_collector.start_request(request_id, component)
            
            try:
                result = await func(*args, **kwargs)
                metrics_collector.end_request(request_id, success=True)
                return result
            except Exception as e:
                metrics_collector.end_request(
                    request_id, 
                    success=False, 
                    metadata={"error": str(e), "error_type": type(e).__name__}
                )
                raise
        
        def sync_wrapper(*args, **kwargs):
            request_id = f"{component.value}_{int(time.time() * 1000)}"
            metrics_collector.start_request(request_id, component)
            
            try:
                result = func(*args, **kwargs)
                metrics_collector.end_request(request_id, success=True)
                return result
            except Exception as e:
                metrics_collector.end_request(
                    request_id, 
                    success=False, 
                    metadata={"error": str(e), "error_type": type(e).__name__}
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def track_quality(component: ComponentType):
    """Decorator voor quality metrics tracking"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Extract quality score from result
            if hasattr(result, 'quality_score'):
                metrics_collector.record_quality_metrics(
                    component=component,
                    overall_score=result.quality_score,
                    metadata={"function": func.__name__}
                )
            
            return result
        
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Extract quality score from result
            if hasattr(result, 'quality_score'):
                metrics_collector.record_quality_metrics(
                    component=component,
                    overall_score=result.quality_score,
                    metadata={"function": func.__name__}
                )
            
            return result
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator