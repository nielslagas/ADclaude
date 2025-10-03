from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
import logging
from datetime import datetime, timedelta

from app.utils.rag_monitoring import (
    metrics_collector, ComponentType, MetricType, AlertLevel,
    PerformanceSnapshot, Alert
)
from app.utils.token_cost_tracker import token_cost_tracker
from app.utils.rag_performance_metrics import rag_performance_tracker
from app.utils.smart_document_classifier import DocumentType
from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


class MetricRequest(BaseModel):
    component: str
    metric_type: str
    value: float
    metadata: Optional[Dict[str, Any]] = {}
    tags: Optional[Dict[str, str]] = {}


class ComponentStatistics(BaseModel):
    component: str
    time_range_hours: int
    total_metrics: int
    statistics: Dict[str, Dict[str, float]]
    recent_errors: int
    request_count: int


class QualityDashboardData(BaseModel):
    time_range_hours: int
    quality_trend: Dict[str, float]
    component_quality: Dict[str, Dict[str, Any]]
    section_quality: Dict[str, Dict[str, float]]
    recent_snapshots: List[Dict[str, Any]]


class AlertResponse(BaseModel):
    timestamp: str
    level: str
    component: str
    message: str
    value: float
    threshold: float
    metadata: Dict[str, Any]


class PerformanceSnapshotResponse(BaseModel):
    timestamp: str
    processing_times: Dict[str, float]
    quality_scores: Dict[str, float]
    error_counts: Dict[str, int]
    throughput: float
    active_requests: int
    memory_usage_mb: float
    token_usage: Dict[str, int]


@router.post("/metrics/record")
async def record_metric(
    request: MetricRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Record een nieuwe metric.
    """
    try:
        # Valideer component
        try:
            component = ComponentType(request.component)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Ongeldige component: {request.component}. "
                       f"Geldige componenten: {[c.value for c in ComponentType]}"
            )
        
        # Valideer metric type
        try:
            metric_type = MetricType(request.metric_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Ongeldig metric type: {request.metric_type}. "
                       f"Geldige types: {[m.value for m in MetricType]}"
            )
        
        # Record metric
        metrics_collector.record_metric(
            component=component,
            metric_type=metric_type,
            value=request.value,
            metadata=request.metadata,
            tags=request.tags
        )
        
        return {"message": "Metric recorded successfully"}
        
    except Exception as e:
        logger.error(f"Fout bij recorden metric: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fout bij recorden metric: {str(e)}")


@router.get("/metrics/snapshot", response_model=PerformanceSnapshotResponse)
async def get_performance_snapshot(
    current_user: dict = Depends(get_current_user)
):
    """
    Krijg een real-time performance snapshot.
    """
    try:
        snapshot = metrics_collector.take_performance_snapshot()
        
        return PerformanceSnapshotResponse(
            timestamp=snapshot.timestamp.isoformat(),
            processing_times={k.value: v for k, v in snapshot.processing_times.items()},
            quality_scores=snapshot.quality_scores,
            error_counts={k.value: v for k, v in snapshot.error_counts.items()},
            throughput=snapshot.throughput,
            active_requests=snapshot.active_requests,
            memory_usage_mb=snapshot.memory_usage_mb,
            token_usage=snapshot.token_usage
        )
        
    except Exception as e:
        logger.error(f"Fout bij ophalen snapshot: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fout bij ophalen snapshot: {str(e)}")


@router.get("/metrics/component/{component}", response_model=ComponentStatistics)
async def get_component_statistics(
    component: str,
    hours: int = Query(1, ge=1, le=168),  # 1 hour to 1 week
    current_user: dict = Depends(get_current_user)
):
    """
    Krijg statistieken voor een specifiek component.
    """
    try:
        # Valideer component
        try:
            component_enum = ComponentType(component)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Ongeldige component: {component}"
            )
        
        stats = metrics_collector.get_component_statistics(component_enum, hours)
        
        if "error" in stats:
            raise HTTPException(status_code=404, detail=stats["error"])
        
        return ComponentStatistics(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fout bij ophalen component statistieken: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fout bij ophalen statistieken: {str(e)}")


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    hours: int = Query(1, ge=1, le=168),
    level: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Krijg recente alerts.
    """
    try:
        # Valideer alert level
        alert_level = None
        if level:
            try:
                alert_level = AlertLevel(level)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ongeldig alert level: {level}. "
                           f"Geldige levels: {[l.value for l in AlertLevel]}"
                )
        
        alerts = metrics_collector.get_recent_alerts(hours, alert_level)
        
        return [AlertResponse(**alert) for alert in alerts]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fout bij ophalen alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fout bij ophalen alerts: {str(e)}")


@router.get("/dashboard/quality", response_model=QualityDashboardData)
async def get_quality_dashboard(
    hours: int = Query(24, ge=1, le=168),
    current_user: dict = Depends(get_current_user)
):
    """
    Krijg quality dashboard data.
    """
    try:
        dashboard_data = metrics_collector.get_quality_dashboard_data(hours)
        
        if "error" in dashboard_data:
            raise HTTPException(status_code=404, detail=dashboard_data["error"])
        
        return QualityDashboardData(**dashboard_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fout bij ophalen quality dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fout bij ophalen dashboard: {str(e)}")


@router.get("/dashboard/overview")
async def get_monitoring_overview(
    current_user: dict = Depends(get_current_user)
):
    """
    Krijg overall monitoring overview.
    """
    try:
        # Get recent snapshot
        snapshot = metrics_collector.take_performance_snapshot()
        
        # Get recent alerts
        recent_alerts = metrics_collector.get_recent_alerts(hours=1)
        critical_alerts = [a for a in recent_alerts if a["level"] == "critical"]
        error_alerts = [a for a in recent_alerts if a["level"] == "error"]
        
        # Calculate system health score
        health_factors = []
        
        # Processing time health
        avg_processing_times = list(snapshot.processing_times.values())
        if avg_processing_times:
            avg_time = sum(avg_processing_times) / len(avg_processing_times)
            time_health = max(0, min(1, (10 - avg_time) / 10))  # 10s = 0, 0s = 1
            health_factors.append(time_health)
        
        # Error rate health
        total_errors = sum(snapshot.error_counts.values())
        error_health = max(0, min(1, (10 - total_errors) / 10))  # 10 errors = 0, 0 errors = 1
        health_factors.append(error_health)
        
        # Alert health
        alert_health = max(0, min(1, (5 - len(critical_alerts)) / 5))  # 5 critical = 0, 0 critical = 1
        health_factors.append(alert_health)
        
        # Quality health
        avg_quality_scores = list(snapshot.quality_scores.values())
        if avg_quality_scores:
            avg_quality = sum(avg_quality_scores) / len(avg_quality_scores)
            quality_health = avg_quality  # Already 0-1
            health_factors.append(quality_health)
        
        overall_health = sum(health_factors) / len(health_factors) if health_factors else 0.5
        
        # Determine status
        if overall_health >= 0.8:
            status = "healthy"
        elif overall_health >= 0.6:
            status = "warning"
        elif overall_health >= 0.4:
            status = "degraded"
        else:
            status = "critical"
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system_health": {
                "score": round(overall_health, 3),
                "status": status,
                "factors": {
                    "processing_time": health_factors[0] if len(health_factors) > 0 else None,
                    "error_rate": health_factors[1] if len(health_factors) > 1 else None,
                    "alerts": health_factors[2] if len(health_factors) > 2 else None,
                    "quality": health_factors[3] if len(health_factors) > 3 else None
                }
            },
            "performance_summary": {
                "active_requests": snapshot.active_requests,
                "throughput_per_minute": round(snapshot.throughput, 2),
                "memory_usage_mb": round(snapshot.memory_usage_mb, 2),
                "total_errors_last_hour": total_errors
            },
            "alerts_summary": {
                "total_alerts_last_hour": len(recent_alerts),
                "critical_alerts": len(critical_alerts),
                "error_alerts": len(error_alerts),
                "recent_critical": critical_alerts[:3]  # Top 3 most recent
            },
            "component_status": {
                component.value: {
                    "avg_processing_time": round(time, 3),
                    "status": "ok" if time < 5.0 else "slow"
                }
                for component, time in snapshot.processing_times.items()
            },
            "quality_summary": {
                "components_with_quality_data": len(snapshot.quality_scores),
                "average_quality": round(
                    sum(snapshot.quality_scores.values()) / len(snapshot.quality_scores), 3
                ) if snapshot.quality_scores else None
            }
        }
        
    except Exception as e:
        logger.error(f"Fout bij ophalen monitoring overview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fout bij ophalen overview: {str(e)}")


@router.get("/metrics/export")
async def export_metrics(
    hours: int = Query(1, ge=1, le=168),
    format: str = Query("json"),
    current_user: dict = Depends(get_current_user)
):
    """
    Export metrics voor externe analyse.
    """
    try:
        if format not in ["json", "prometheus"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: {format}. Supported: json, prometheus"
            )
        
        exported_data = metrics_collector.export_metrics(hours, format)
        
        if format == "prometheus":
            # Return Prometheus format directly
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(
                content=exported_data,
                media_type="text/plain; version=0.0.4; charset=utf-8"
            )
        
        return {
            "format": format,
            "time_range_hours": hours,
            "export_timestamp": datetime.utcnow().isoformat(),
            "data": exported_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fout bij export metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fout bij export: {str(e)}")


@router.get("/components")
async def get_available_components(
    current_user: dict = Depends(get_current_user)
):
    """
    Krijg lijst van beschikbare componenten voor monitoring.
    """
    return {
        "components": [
            {
                "value": component.value,
                "display_name": component.value.replace("_", " ").title(),
                "description": _get_component_description(component)
            }
            for component in ComponentType
        ],
        "metric_types": [
            {
                "value": metric.value,
                "display_name": metric.value.replace("_", " ").title(),
                "description": _get_metric_description(metric)
            }
            for metric in MetricType
        ],
        "alert_levels": [
            {
                "value": level.value,
                "display_name": level.value.title(),
                "description": _get_alert_description(level)
            }
            for level in AlertLevel
        ]
    }


def _get_component_description(component: ComponentType) -> str:
    """Krijg beschrijving voor component"""
    descriptions = {
        ComponentType.DOCUMENT_CLASSIFIER: "Classifies and analyzes document types",
        ComponentType.RAG_PIPELINE: "Retrieval-Augmented Generation pipeline",
        ComponentType.PROMPT_GENERATOR: "Context-aware prompt generation",
        ComponentType.QUALITY_CONTROLLER: "Content quality validation and improvement",
        ComponentType.MULTIMODAL_RAG: "Multi-modal content processing",
        ComponentType.VECTOR_STORE: "Vector storage and similarity search",
        ComponentType.LLM_PROVIDER: "Large Language Model interactions",
        ComponentType.AUDIO_TRANSCRIBER: "Audio transcription services"
    }
    return descriptions.get(component, "System component")


def _get_metric_description(metric: MetricType) -> str:
    """Krijg beschrijving voor metric type"""
    descriptions = {
        MetricType.PROCESSING_TIME: "Time taken to process requests",
        MetricType.QUALITY_SCORE: "Quality score of generated content",
        MetricType.ERROR_RATE: "Rate of errors and failures",
        MetricType.THROUGHPUT: "Number of requests processed per unit time",
        MetricType.MEMORY_USAGE: "Memory consumption",
        MetricType.TOKEN_USAGE: "LLM token consumption",
        MetricType.USER_SATISFACTION: "User satisfaction ratings",
        MetricType.CACHE_HIT_RATE: "Cache hit rate percentage"
    }
    return descriptions.get(metric, "System metric")


def _get_alert_description(level: AlertLevel) -> str:
    """Krijg beschrijving voor alert level"""
    descriptions = {
        AlertLevel.INFO: "Informational alerts",
        AlertLevel.WARNING: "Warning conditions that need attention",
        AlertLevel.ERROR: "Error conditions requiring action",
        AlertLevel.CRITICAL: "Critical issues requiring immediate action"
    }
    return descriptions.get(level, "Alert level")


@router.post("/metrics/reset")
async def reset_metrics(
    current_user: dict = Depends(get_current_user)
):
    """
    Reset alle metrics (alleen voor testing/development).
    """
    try:
        metrics_collector.reset_metrics()
        return {"message": "All metrics have been reset"}
    except Exception as e:
        logger.error(f"Fout bij reset metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fout bij reset: {str(e)}")


@router.post("/quality/record")
async def record_quality_metrics(
    component: str,
    overall_score: float,
    section_scores: Optional[Dict[str, float]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Record quality metrics voor een component.
    """
    try:
        # Valideer component
        try:
            component_enum = ComponentType(component)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Ongeldige component: {component}"
            )
        
        # Valideer score
        if not 0 <= overall_score <= 1:
            raise HTTPException(
                status_code=400,
                detail="Overall score must be between 0 and 1"
            )
        
        # Convert section scores if provided
        converted_section_scores = None
        if section_scores:
            from app.utils.context_aware_prompts import ReportSection
            converted_section_scores = {}
            for section_name, score in section_scores.items():
                try:
                    section_enum = ReportSection(section_name)
                    converted_section_scores[section_enum] = score
                except ValueError:
                    logger.warning(f"Unknown section: {section_name}")
        
        # Record quality metrics
        metrics_collector.record_quality_metrics(
            component=component_enum,
            overall_score=overall_score,
            section_scores=converted_section_scores,
            metadata=metadata
        )
        
        return {"message": "Quality metrics recorded successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fout bij recorden quality metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fout bij recorden quality metrics: {str(e)}")


@router.post("/tokens/record")
async def record_token_usage(
    component: str,
    input_tokens: int,
    output_tokens: int,
    metadata: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Record token usage voor LLM components.
    """
    try:
        # Valideer component
        try:
            component_enum = ComponentType(component)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Ongeldige component: {component}"
            )
        
        # Valideer token counts
        if input_tokens < 0 or output_tokens < 0:
            raise HTTPException(
                status_code=400,
                detail="Token counts must be non-negative"
            )
        
        # Record token usage
        metrics_collector.record_token_usage(
            component=component_enum,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            metadata=metadata
        )
        
        return {"message": "Token usage recorded successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fout bij recorden token usage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fout bij recorden token usage: {str(e)}")


@router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint (no authentication required for scraping).
    Returns metrics in Prometheus exposition format.
    """
    try:
        prometheus_data = metrics_collector.export_prometheus_metrics()
        
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            content=prometheus_data,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
        
    except Exception as e:
        logger.error(f"Fout bij ophalen Prometheus metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fout bij Prometheus metrics: {str(e)}")


@router.get("/health/rag")
async def rag_health_check():
    """
    RAG pipeline health check for monitoring systems.
    """
    try:
        health_status = metrics_collector.get_rag_health_status()
        
        if health_status["status"] != "healthy":
            raise HTTPException(
                status_code=503,
                detail=f"RAG pipeline unhealthy: {health_status['message']}"
            )
        
        return health_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fout bij RAG health check: {str(e)}")
        raise HTTPException(status_code=500, detail=f"RAG health check failed: {str(e)}")


@router.get("/performance/profile")
async def get_performance_profile(
    component: Optional[str] = Query(None),
    duration_minutes: int = Query(5, ge=1, le=60),
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed performance profile for RAG components.
    """
    try:
        component_enum = None
        if component:
            try:
                component_enum = ComponentType(component)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ongeldige component: {component}"
                )
        
        profile_data = metrics_collector.get_performance_profile(
            component=component_enum,
            duration_minutes=duration_minutes
        )
        
        return profile_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fout bij performance profiling: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Performance profiling failed: {str(e)}")


@router.get("/tokens/usage")
async def get_token_usage_statistics(
    hours: int = Query(24, ge=1, le=168),
    current_user: dict = Depends(get_current_user)
):
    """
    Get comprehensive token usage and cost statistics.
    """
    try:
        cost_analysis = token_cost_tracker.get_cost_analysis(hours)
        provider_comparison = token_cost_tracker.get_provider_comparison()
        
        return {
            "cost_analysis": cost_analysis,
            "provider_comparison": provider_comparison,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Fout bij ophalen token usage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Token usage statistics failed: {str(e)}")


@router.get("/tokens/costs")
async def get_cost_breakdown(
    hours: int = Query(24, ge=1, le=168),
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed cost breakdown and optimization suggestions.
    """
    try:
        cost_analysis = token_cost_tracker.get_cost_analysis(hours)
        
        # Calculate additional cost metrics
        cost_efficiency = {}
        if cost_analysis.total_cost > 0 and cost_analysis.total_tokens > 0:
            cost_efficiency = {
                "cost_per_token": cost_analysis.total_cost / cost_analysis.total_tokens,
                "tokens_per_dollar": cost_analysis.total_tokens / cost_analysis.total_cost,
                "cost_per_request": cost_analysis.average_cost_per_request
            }
        
        return {
            "cost_breakdown": {
                "total_cost_usd": round(cost_analysis.total_cost, 4),
                "total_tokens": cost_analysis.total_tokens,
                "cost_by_provider": cost_analysis.cost_by_provider,
                "cost_by_component": cost_analysis.cost_by_component,
                "cost_by_model": cost_analysis.cost_by_model,
                "cost_trend": cost_analysis.cost_trend
            },
            "efficiency_metrics": cost_efficiency,
            "optimization_suggestions": cost_analysis.optimization_suggestions,
            "time_period": cost_analysis.time_period,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Fout bij cost breakdown: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cost breakdown failed: {str(e)}")


@router.post("/tokens/record-usage")
async def record_token_usage_detailed(
    provider: str,
    model_name: str,
    component: str,
    input_tokens: int,
    output_tokens: int,
    request_id: str,
    quality_score: Optional[float] = None,
    response_time: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Record detailed token usage with cost tracking.
    """
    try:
        # Validate component
        try:
            component_enum = ComponentType(component)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Ongeldige component: {component}"
            )
        
        # Prepare metadata
        detailed_metadata = metadata or {}
        if quality_score is not None:
            detailed_metadata["quality_score"] = quality_score
        if response_time is not None:
            detailed_metadata["response_time"] = response_time
        
        # Record usage
        usage_record = token_cost_tracker.record_token_usage(
            provider=provider,
            model_name=model_name,
            component=component_enum,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            request_id=request_id,
            metadata=detailed_metadata
        )
        
        return {
            "message": "Token usage recorded successfully",
            "cost_usd": round(usage_record.total_cost, 4),
            "total_tokens": usage_record.total_tokens,
            "timestamp": usage_record.timestamp.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fout bij recorden detailed token usage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Detailed token usage recording failed: {str(e)}")


@router.get("/tokens/export")
async def export_token_cost_data(
    hours: int = Query(24, ge=1, le=168),
    format: str = Query("json"),
    current_user: dict = Depends(get_current_user)
):
    """
    Export token cost data for external analysis.
    """
    try:
        if format not in ["json"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: {format}. Supported: json"
            )
        
        export_data = token_cost_tracker.export_cost_data(hours, format)
        
        if format == "json":
            from fastapi.responses import Response
            return Response(
                content=export_data,
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=token_costs_{hours}h.json"}
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fout bij export token cost data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Token cost export failed: {str(e)}")


@router.get("/rag/performance-analysis")
async def get_rag_performance_analysis(
    document_type: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=168),
    current_user: dict = Depends(get_current_user)
):
    """
    Get comprehensive RAG performance analysis including retrieval accuracy and generation quality.
    """
    try:
        # Validate document type if provided
        doc_type_enum = None
        if document_type:
            try:
                doc_type_enum = DocumentType(document_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid document type: {document_type}"
                )
        
        analysis = rag_performance_tracker.get_performance_analysis(
            document_type=doc_type_enum,
            hours=hours
        )
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fout bij RAG performance analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"RAG performance analysis failed: {str(e)}")


@router.get("/rag/retrieval-metrics")
async def get_retrieval_metrics_summary(
    hours: int = Query(24, ge=1, le=168),
    current_user: dict = Depends(get_current_user)
):
    """
    Get summary of retrieval performance metrics.
    """
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get recent retrieval metrics
        recent_retrievals = [
            r for r in rag_performance_tracker.retrieval_history
            if r.timestamp > cutoff_time
        ]
        
        if not recent_retrievals:
            return {
                "message": "No retrieval data available",
                "time_period": f"Last {hours} hours",
                "metrics_count": 0
            }
        
        # Calculate summary statistics
        precision_scores = [r.precision_at_k for r in recent_retrievals]
        recall_scores = [r.recall_at_k for r in recent_retrievals]
        mrr_scores = [r.mrr_score for r in recent_retrievals]
        ndcg_scores = [r.ndcg_score for r in recent_retrievals]
        similarity_scores = [r.avg_similarity_score for r in recent_retrievals]
        
        # Group by document type
        by_doc_type = defaultdict(list)
        for retrieval in recent_retrievals:
            by_doc_type[retrieval.document_type.value].append(retrieval)
        
        doc_type_stats = {}
        for doc_type, retrievals in by_doc_type.items():
            doc_type_stats[doc_type] = {
                "count": len(retrievals),
                "avg_precision": statistics.mean([r.precision_at_k for r in retrievals]),
                "avg_recall": statistics.mean([r.recall_at_k for r in retrievals]),
                "avg_mrr": statistics.mean([r.mrr_score for r in retrievals])
            }
        
        return {
            "time_period": f"Last {hours} hours",
            "metrics_count": len(recent_retrievals),
            "overall_performance": {
                "avg_precision_at_k": statistics.mean(precision_scores),
                "avg_recall_at_k": statistics.mean(recall_scores),
                "avg_mrr_score": statistics.mean(mrr_scores),
                "avg_ndcg_score": statistics.mean(ndcg_scores),
                "avg_similarity_score": statistics.mean(similarity_scores),
                "precision_std_dev": statistics.stdev(precision_scores) if len(precision_scores) > 1 else 0,
                "recall_std_dev": statistics.stdev(recall_scores) if len(recall_scores) > 1 else 0
            },
            "performance_by_document_type": doc_type_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Fout bij retrieval metrics summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Retrieval metrics summary failed: {str(e)}")


@router.get("/rag/generation-quality")
async def get_generation_quality_summary(
    hours: int = Query(24, ge=1, le=168),
    current_user: dict = Depends(get_current_user)
):
    """
    Get summary of generation quality metrics.
    """
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get recent generation metrics
        recent_generations = [
            g for g in rag_performance_tracker.generation_history
            if g.timestamp > cutoff_time
        ]
        
        if not recent_generations:
            return {
                "message": "No generation data available",
                "time_period": f"Last {hours} hours",
                "metrics_count": 0
            }
        
        # Calculate overall quality metrics
        quality_dimensions = [
            "factual_accuracy", "completeness", "coherence", 
            "relevance", "technical_accuracy", "legal_compliance"
        ]
        
        overall_quality = {}
        for dimension in quality_dimensions:
            scores = [getattr(g, dimension) for g in recent_generations if getattr(g, dimension) > 0]
            if scores:
                overall_quality[dimension] = {
                    "average": statistics.mean(scores),
                    "median": statistics.median(scores),
                    "std_dev": statistics.stdev(scores) if len(scores) > 1 else 0,
                    "min": min(scores),
                    "max": max(scores),
                    "sample_count": len(scores)
                }
        
        # Group by report section
        by_section = defaultdict(list)
        for generation in recent_generations:
            by_section[generation.report_section.value].append(generation)
        
        section_quality = {}
        for section, generations in by_section.items():
            section_scores = []
            for gen in generations:
                gen_scores = [
                    getattr(gen, dim) for dim in quality_dimensions 
                    if getattr(gen, dim) > 0
                ]
                if gen_scores:
                    section_scores.append(statistics.mean(gen_scores))
            
            if section_scores:
                section_quality[section] = {
                    "avg_quality": statistics.mean(section_scores),
                    "generation_count": len(generations),
                    "avg_generation_time": statistics.mean([g.generation_time for g in generations]),
                    "avg_token_count": statistics.mean([g.token_count for g in generations])
                }
        
        return {
            "time_period": f"Last {hours} hours",
            "metrics_count": len(recent_generations),
            "overall_quality_dimensions": overall_quality,
            "quality_by_section": section_quality,
            "generation_statistics": {
                "total_tokens_generated": sum(g.token_count for g in recent_generations),
                "avg_generation_time": statistics.mean([g.generation_time for g in recent_generations]),
                "total_generation_time": sum(g.generation_time for g in recent_generations)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Fout bij generation quality summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Generation quality summary failed: {str(e)}")


@router.get("/rag/pipeline-performance")
async def get_pipeline_performance_summary(
    hours: int = Query(24, ge=1, le=168),
    current_user: dict = Depends(get_current_user)
):
    """
    Get end-to-end pipeline performance summary.
    """
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get recent pipeline metrics
        recent_pipelines = [
            p for p in rag_performance_tracker.pipeline_history
            if p.timestamp > cutoff_time
        ]
        
        if not recent_pipelines:
            return {
                "message": "No pipeline data available",
                "time_period": f"Last {hours} hours",
                "pipeline_count": 0
            }
        
        # Calculate performance statistics
        quality_scores = [p.overall_quality_score for p in recent_pipelines]
        processing_times = [p.total_processing_time for p in recent_pipelines]
        costs = [p.total_cost for p in recent_pipelines]
        user_satisfaction_scores = [p.user_satisfaction for p in recent_pipelines if p.user_satisfaction is not None]
        
        # Group by processing strategy
        by_strategy = defaultdict(list)
        for pipeline in recent_pipelines:
            by_strategy[pipeline.processing_strategy.value].append(pipeline)
        
        strategy_performance = {}
        for strategy, pipelines in by_strategy.items():
            strategy_performance[strategy] = {
                "pipeline_count": len(pipelines),
                "avg_quality": statistics.mean([p.overall_quality_score for p in pipelines]),
                "avg_processing_time": statistics.mean([p.total_processing_time for p in pipelines]),
                "avg_cost": statistics.mean([p.total_cost for p in pipelines]),
                "total_cost": sum([p.total_cost for p in pipelines])
            }
        
        # Group by document type
        by_doc_type = defaultdict(list)
        for pipeline in recent_pipelines:
            by_doc_type[pipeline.document_type.value].append(pipeline)
        
        doc_type_performance = {}
        for doc_type, pipelines in by_doc_type.items():
            doc_type_performance[doc_type] = {
                "pipeline_count": len(pipelines),
                "avg_quality": statistics.mean([p.overall_quality_score for p in pipelines]),
                "avg_processing_time": statistics.mean([p.total_processing_time for p in pipelines])
            }
        
        return {
            "time_period": f"Last {hours} hours",
            "pipeline_count": len(recent_pipelines),
            "overall_performance": {
                "avg_quality_score": statistics.mean(quality_scores),
                "median_quality_score": statistics.median(quality_scores),
                "quality_std_dev": statistics.stdev(quality_scores) if len(quality_scores) > 1 else 0,
                "avg_processing_time": statistics.mean(processing_times),
                "median_processing_time": statistics.median(processing_times),
                "total_processing_time": sum(processing_times),
                "avg_cost": statistics.mean(costs),
                "total_cost": sum(costs),
                "avg_user_satisfaction": statistics.mean(user_satisfaction_scores) if user_satisfaction_scores else None
            },
            "performance_by_strategy": strategy_performance,
            "performance_by_document_type": doc_type_performance,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Fout bij pipeline performance summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Pipeline performance summary failed: {str(e)}")